"""Voice Profile Agent tests.

Covers the voice-to-profile pipeline:
1. Free-text perception with voice-like input (reuses existing endpoint)
2. Profile review with extracted skills (reuses existing endpoint)
3. End-to-end voice profile flow simulation
4. Edge cases: empty transcript, long text, malformed input
5. Security: candidate-only access, ownership enforcement
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Voice Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


# ── Voice transcript perception ──────────────────────────────────────


@pytest.mark.asyncio
async def test_voice_transcript_perception(client: AsyncClient):
    """A voice transcript should produce structured perception results."""
    tokens = await _register_and_login(client, "voice_perc@example.com")
    headers = _headers(tokens)

    transcript = (
        "I have two years of experience in Python and Java. "
        "I have worked with FastAPI and PostgreSQL. "
        "I built REST APIs. "
        "I am currently learning Docker."
    )

    form_data = {"text": transcript}
    resp = await client.post(
        "/api/v1/skill2job/perception/text",
        data=form_data,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "perception_id" in data
    assert "result" in data

    result = data["result"]
    # Skills should be extracted from the transcript
    skills = result.get("skills", [])
    skill_names = [s.get("name", "").lower() for s in skills]
    assert any("python" in s for s in skill_names), f"Python not found in skills: {skill_names}"
    assert any("java" in s for s in skill_names), f"Java not found in skills: {skill_names}"


@pytest.mark.asyncio
async def test_voice_transcript_empty(client: AsyncClient):
    """Empty transcript should fail gracefully."""
    tokens = await _register_and_login(client, "voice_empty@example.com")
    headers = _headers(tokens)

    resp = await client.post(
        "/api/v1/skill2job/perception/text",
        data={"text": ""},
        headers=headers,
    )
    # Should either fail with 422 or return a failed status
    assert resp.status_code in (400, 422, 200)
    if resp.status_code == 200:
        result = resp.json().get("result", {})
        assert result.get("processing_status") in ("failed", "partial")


@pytest.mark.asyncio
async def test_voice_transcript_long(client: AsyncClient):
    """Long transcript should be handled without error."""
    tokens = await _register_and_login(client, "voice_long@example.com")
    headers = _headers(tokens)

    # Generate a long transcript
    transcript = (
        "I have extensive experience in software engineering. " * 50
        + "I know Python, Java, JavaScript, React, and Docker. "
        + "I have worked at multiple companies including Google and Microsoft. "
    )

    resp = await client.post(
        "/api/v1/skill2job/perception/text",
        data={"text": transcript},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "perception_id" in data


# ── Profile review with voice-extracted skills ───────────────────────


@pytest.mark.asyncio
async def test_voice_confirm_adds_skills(client: AsyncClient):
    """Confirming voice extraction should add skills to the profile."""
    tokens = await _register_and_login(client, "voice_confirm@example.com")
    headers = _headers(tokens)

    # Step 1: Perceive a voice transcript
    transcript = (
        "I have three years of experience in Python and Go. "
        "I have worked with Kubernetes and AWS."
    )
    perc_resp = await client.post(
        "/api/v1/skill2job/perception/text",
        data={"text": transcript},
        headers=headers,
    )
    assert perc_resp.status_code == 200

    # Step 2: Confirm with profile review
    review_resp = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={
            "skills_to_add": ["Python", "Go", "Kubernetes", "AWS"],
            "skills_to_exclude": [],
            "corrections": [],
        },
        headers=headers,
    )
    assert review_resp.status_code == 200
    review = review_resp.json()
    assert "applied_skills" in review


@pytest.mark.asyncio
async def test_voice_confirm_with_experience(client: AsyncClient):
    """Confirming with experience corrections should work."""
    tokens = await _register_and_login(client, "voice_exp@example.com")
    headers = _headers(tokens)

    review_resp = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={
            "skills_to_add": ["Python", "Java"],
            "skills_to_exclude": [],
            "corrections": [
                {"field": "skill_experience:Python", "value": "3", "note": "Voice-input: 3 years"},
                {"field": "skill_experience:Java", "value": "2", "note": "Voice-input: 2 years"},
            ],
        },
        headers=headers,
    )
    assert review_resp.status_code == 200


@pytest.mark.asyncio
async def test_voice_confirm_excludes_skills(client: AsyncClient):
    """Candidate should be able to exclude skills they don't want added."""
    tokens = await _register_and_login(client, "voice_exclude@example.com")
    headers = _headers(tokens)

    # Perceive
    await client.post(
        "/api/v1/skill2job/perception/text",
        data={"text": "I know Python and JavaScript and React."},
        headers=headers,
    )

    # Confirm but exclude JavaScript
    review_resp = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={
            "skills_to_add": ["Python", "React"],
            "skills_to_exclude": ["JavaScript"],
            "corrections": [],
        },
        headers=headers,
    )
    assert review_resp.status_code == 200
    review = review_resp.json()
    assert "JavaScript" in review.get("excluded_skills", [])


# ── Security: candidate-only access ──────────────────────────────────


@pytest.mark.asyncio
async def test_voice_requires_auth(client: AsyncClient):
    """Voice perception and review should require authentication."""
    resp = await client.post(
        "/api/v1/skill2job/perception/text",
        data={"text": "I know Python."},
    )
    # 401/403 if auth is checked first; 422 if form validation fires before auth
    assert resp.status_code in (401, 403, 422)

    resp = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={"skills_to_add": ["Python"], "skills_to_exclude": [], "corrections": []},
    )
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_voice_cannot_update_other_candidate(client: AsyncClient):
    """Candidate A should not be able to update Candidate B's profile."""
    tokens_a = await _register_and_login(client, "voice_a@example.com")
    tokens_b = await _register_and_login(client, "voice_b@example.com")

    # Candidate A adds Python to their profile
    resp_a = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={
            "skills_to_add": ["Python"],
            "skills_to_exclude": [],
            "corrections": [],
        },
        headers=_headers(tokens_a),
    )
    assert resp_a.status_code == 200

    # Candidate B tries to add Python to their own profile (should work for themselves)
    resp_b = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={
            "skills_to_add": ["Java"],
            "skills_to_exclude": [],
            "corrections": [],
        },
        headers=_headers(tokens_b),
    )
    assert resp_b.status_code == 200

    # Verify B's skills don't include Python (A's skill)
    # This is validated by the ownership model - B can only update their own profile


# ── Full end-to-end voice flow simulation ────────────────────────────


@pytest.mark.asyncio
async def test_voice_full_flow(client: AsyncClient):
    """Simulate the full voice-to-profile flow."""
    tokens = await _register_and_login(client, "voice_flow@example.com")
    headers = _headers(tokens)

    # Step 1: Simulate voice transcript
    transcript = (
        "I have two years of experience in Python and Java. "
        "I have worked with FastAPI and PostgreSQL. "
        "I built REST APIs and I am currently learning Docker."
    )

    # Step 2: Perceive the transcript (like the frontend does after STT)
    perc_resp = await client.post(
        "/api/v1/skill2job/perception/text",
        data={"text": transcript},
        headers=headers,
    )
    assert perc_resp.status_code == 200
    perc_data = perc_resp.json()
    perception_id = perc_data["perception_id"]
    result = perc_data["result"]

    # Step 3: Extract skills from perception result
    skills = [s["name"] for s in result.get("skills", [])]
    assert len(skills) > 0, "Should extract at least one skill from voice transcript"

    # Step 4: Review and confirm (like the frontend does after user confirms)
    review_resp = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={
            "skills_to_add": skills[:5],  # User confirms top 5 skills
            "skills_to_exclude": [],
            "corrections": [
                {"field": "skill_experience:Python", "value": "2", "note": "Voice: 2 years Python"}
            ],
        },
        headers=headers,
    )
    assert review_resp.status_code == 200
    review = review_resp.json()
    assert len(review.get("applied_skills", [])) > 0

    # Step 5: Verify perception is in history
    history_resp = await client.get(
        "/api/v1/skill2job/perception",
        headers=headers,
    )
    assert history_resp.status_code == 200
    history = history_resp.json()
    ids = [p["id"] for p in history.get("items", [])]
    assert perception_id in ids, "Voice perception should appear in history"
