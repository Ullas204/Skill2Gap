"""Phase 3 — Candidate Evidence Intelligence tests.

Covers the engine (deterministic) and the API endpoints (authorization,
caching, LLM-contract safety), with dedicated anti-hallucination and
sensitive-attribute safety tests.
"""

import json
import uuid

import pytest

from app.repositories.user import UserRepository
from app.services.screening.intel_engine import (
    CandidateIntelEngine,
    build_profile_from_dict,
    extract_stated_years,
    run_intel_analysis,
)
from app.services.screening.intel_service import CandidateIntelService


# ─── shared builders ──────────────────────────────────────────────────────


def _skill(name, category="Other", source_section="Skills"):
    return {
        "name": name,
        "category": category,
        "matched_on": name.lower(),
        "inferred": False,
        "source_section": source_section,
        "source_text": None,
    }


def _profile_json(
    summary="Engineer.",
    skills=None,
    experience=None,
    projects=None,
    certifications=None,
    education=None,
):
    return {
        "schema_version": "1",
        "summary": summary,
        "personal_info": None,
        "skills": skills or [],
        "experience": experience or [],
        "education": education or [],
        "projects": projects or [],
        "certifications": certifications or [],
        "languages": [],
        "metadata": {
            "parser_version": "rie-1.0.0",
            "processed_at": "2026-08-24T00:00:00Z",
            "language": None,
            "detected_sections": [],
            "warnings": [],
        },
    }


def _experience_entry(**overrides):
    entry = {
        "company": "ABC Technologies",
        "job_title": "Backend Engineer",
        "title": None,
        "location": None,
        "employment_type": None,
        "start_date": "2022-01",
        "end_date": None,
        "original_start_date": None,
        "original_end_date": None,
        "is_current": True,
        "dates_uncertain": False,
        "duration_months": 40,
        "duration_label": "~3 years 4 months",
        "description": ["Developed asynchronous APIs using Python and FastAPI."],
        "responsibilities": [],
        "achievements": [],
        "technologies": ["Python", "FastAPI"],
        "source_section": "Experience",
        "source_text": None,
    }
    entry.update(overrides)
    return entry


def _analyze(profile_json=None, raw_text=""):
    return run_intel_analysis(profile_json, raw_text)


def _assessment(result, skill_name):
    for a in result["skill_assessments"]:
        if a["skill"].lower() == skill_name.lower():
            return a
    raise AssertionError(f"no assessment for {skill_name}")


# ─── skill depth tiers ────────────────────────────────────────────────────


class TestSkillDepthTiers:
    def test_expert_level_requires_long_multi_role_evidence(self):
        profile = _profile_json(
            skills=[_skill("Python", "Programming Language")],
            experience=[
                _experience_entry(
                    job_title="Backend Engineer", company="A", is_current=False,
                    start_date="2018-01", end_date="2021-06", duration_months=None,
                    technologies=["Python"],
                ),
                _experience_entry(
                    job_title="Senior Backend Engineer", company="B", is_current=True,
                    start_date="2021-07", duration_months=None, technologies=["Python"],
                ),
            ],
        )
        result = _analyze(profile)
        a = _assessment(result, "Python")
        assert a["depth"] == "expert_level_evidence"
        assert a["professional_months"] >= 36

    def test_strong_from_single_solid_role(self):
        profile = _profile_json(
            skills=[_skill("Python", "Programming Language")],
            experience=[_experience_entry(duration_months=18)],
        )
        a = _assessment(_analyze(profile), "Python")
        assert a["depth"] == "strong"

    def test_moderate_from_multiple_projects(self):
        profile = _profile_json(
            skills=[_skill("Rust", "Programming Language")],
            projects=[
                {"name": "P1", "description": ["Systems tooling in Rust."],
                 "technologies": ["Rust"], "responsibilities": [], "achievements": []},
                {"name": "P2", "description": ["CLI written in Rust."],
                 "technologies": ["Rust"], "responsibilities": [], "achievements": []},
            ],
        )
        a = _assessment(_analyze(profile), "Rust")
        assert a["depth"] == "moderate"

    def test_limited_from_single_project(self):
        profile = _profile_json(
            skills=[_skill("Rust", "Programming Language")],
            projects=[
                {"name": "P1", "description": ["Systems tooling in Rust."],
                 "technologies": ["Rust"], "responsibilities": [], "achievements": []},
            ],
        )
        a = _assessment(_analyze(profile), "Rust")
        assert a["depth"] in ("limited", "moderate")

    def test_mention_only_when_skills_section_only(self):
        profile = _profile_json(skills=[_skill("Kubernetes", "DevOps")])
        a = _assessment(_analyze(profile), "Kubernetes")
        assert a["depth"] == "mention_only"


# ─── confidence tiers ─────────────────────────────────────────────────────


class TestConfidenceTiers:
    def test_high_confidence_needs_two_roles_or_role_plus_project(self):
        profile = _profile_json(
            skills=[_skill("Python", "Programming Language")],
            experience=[
                _experience_entry(company="A"),
                _experience_entry(
                    company="B", technologies=["Python"],
                    description=["Python services."],
                ),
            ],
        )
        a = _assessment(_analyze(profile), "Python")
        assert a["confidence"] == "high"

    def test_insufficient_for_raw_text_only(self):
        result = _analyze(
            _profile_json(),
            raw_text="Mentions Kubernetes somewhere deep in prose.",
        )
        a = _assessment(result, "kubernetes")
        assert a["confidence"] == "insufficient"

    def test_low_confidence_for_skills_listing(self):
        profile = _profile_json(skills=[_skill("Terraform", "DevOps")])
        a = _assessment(_analyze(profile), "Terraform")
        assert a["confidence"] == "low"


# ─── timeline consistency ─────────────────────────────────────────────────


class TestTimelineConsistency:
    def test_stated_vs_timeline_mismatch_flagged(self):
        profile = _profile_json(
            summary="Engineer with 10+ years of experience.",
            experience=[_experience_entry(is_current=False, start_date="2024-01",
                                          end_date="2025-01", duration_months=None)],
        )
        result = _analyze(profile)
        types = [f["flag_type"] for f in result["review_flags"]]
        assert "stated_vs_timeline_mismatch" in types

    def test_age_is_not_read_as_experience(self):
        text = "I am 45 years old and have 6 years of platform engineering experience."
        assert extract_stated_years(text, None) == 6.0

    def test_overlapping_employment_detected(self):
        profile = _profile_json(
            experience=[
                _experience_entry(company="A", is_current=False,
                                  start_date="2022-01", end_date="2023-12",
                                  duration_months=None),
                _experience_entry(company="B", is_current=False,
                                  start_date="2023-01", end_date="2024-12",
                                  duration_months=None),
            ],
        )
        result = _analyze(profile)
        types = [f["flag_type"] for f in result["review_flags"]]
        assert "overlapping_employment" in types
        flag = next(f for f in result["review_flags"]
                    if f["flag_type"] == "overlapping_employment")
        assert "possible_explanation" in flag and flag["possible_explanation"]

    def test_reversed_dates_flagged(self):
        profile = _profile_json(
            experience=[_experience_entry(
                is_current=False, start_date="2022-06", end_date="2022-01",
                duration_months=None,
            )],
        )
        result = _analyze(profile)
        types = [f["flag_type"] for f in result["review_flags"]]
        assert "date_inconsistency" in types

    def test_missing_dates_flagged(self):
        profile = _profile_json(experience=[
            _experience_entry(start_date=None, end_date=None, duration_months=24),
        ])
        result = _analyze(profile)
        types = [f["flag_type"] for f in result["review_flags"]]
        assert "missing_dates" in types

    def test_employment_gap_flagged(self):
        profile = _profile_json(experience=[
            _experience_entry(company="A", is_current=False,
                              start_date="2019-01", end_date="2020-01",
                              duration_months=None),
            _experience_entry(company="B", is_current=False,
                              start_date="2023-01", end_date="2024-01",
                              duration_months=None),
        ])
        result = _analyze(profile)
        types = [f["flag_type"] for f in result["review_flags"]]
        assert "employment_gap" in types

    def test_total_experience_is_union_not_double_counted(self):
        profile = _profile_json(experience=[
            _experience_entry(company="A", is_current=False,
                              start_date="2022-01", end_date="2023-01",
                              duration_months=None),
            _experience_entry(company="B", is_current=False,
                              start_date="2022-06", end_date="2023-06",
                              duration_months=None),
        ])
        snapshot = _analyze(profile)["snapshot"]
        # Overlap of ~8 months must not be counted twice.
        assert snapshot["total_experience_months"] <= 19


# ─── safety guarantees ────────────────────────────────────────────────────


class TestSafetyGuarantees:
    def test_no_lacks_claim_for_thin_evidence(self):
        profile = _profile_json(skills=[_skill("Kubernetes", "DevOps")])
        blob = json.dumps(_analyze(profile)).lower()
        assert "lacks" not in blob
        assert "does not have" not in blob

    def test_gap_note_makes_no_claim(self):
        profile = _profile_json(skills=[_skill("Kubernetes", "DevOps")])
        gaps = _analyze(profile)["evidence_gaps"]
        assert gaps and "no claim is made" in gaps[0]["note"].lower()

    def test_achievements_labelled_candidate_stated(self):
        profile = _profile_json(
            experience=[_experience_entry(achievements=["Reduced deploy time by 40%"])],
        )
        achievements = _analyze(profile)["achievements"]
        assert achievements
        assert all(a["label"] == "Candidate-stated" for a in achievements)

    def test_no_sensitive_attributes_in_output(self):
        profile = _profile_json(
            summary="I am 45 years old, married with two kids. Platform engineer.",
            skills=[_skill("Python", "Programming Language")],
            experience=[_experience_entry()],
        )
        blob = json.dumps(_analyze(profile)).lower()
        for banned in ("gender", "pregnant", "religion", "ethnic", "nationality",
                       "disability", "married", "age is", "years old"):
            assert banned not in blob, f"sensitive term leaked: {banned}"

    def test_no_universal_score_or_hiring_recommendation(self):
        profile = _profile_json(
            skills=[_skill("Python", "Programming Language")],
            experience=[_experience_entry()],
        )
        blob = json.dumps(_analyze(profile)).lower()
        for banned in ("recommend hiring", "should hire", "do not hire", "fit score"):
            assert banned not in blob

    def test_review_flags_are_never_accusatory(self):
        profile = _profile_json(
            experience=[
                _experience_entry(company="A", is_current=False,
                                  start_date="2022-01", end_date="2023-12",
                                  duration_months=None),
                _experience_entry(company="B", is_current=False,
                                  start_date="2023-01", end_date="2024-12",
                                  duration_months=None),
            ],
        )
        blob = json.dumps(_analyze(profile)).lower()
        for banned in ("fraud", "dishonest", "lie", "fake", "misrepresent"):
            assert banned not in blob


# ─── screening questions ──────────────────────────────────────────────────


class TestQuestionGeneration:
    def test_question_for_mention_only_skill(self):
        profile = _profile_json(skills=[_skill("Kubernetes", "DevOps")])
        questions = _analyze(profile)["screening_questions"]
        assert any("kubernetes" in q["question"].lower() for q in questions)

    def test_question_for_quantified_achievement(self):
        profile = _profile_json(
            experience=[_experience_entry(achievements=["Cut costs by 30% via caching"])],
        )
        questions = _analyze(profile)["screening_questions"]
        assert any("cut costs by 30%" in q["question"].lower() for q in questions)

    def test_clarification_question_for_overlap(self):
        profile = _profile_json(experience=[
            _experience_entry(company="A", is_current=False,
                              start_date="2022-01", end_date="2023-12",
                              duration_months=None),
            _experience_entry(company="B", is_current=False,
                              start_date="2023-01", end_date="2024-12",
                              duration_months=None),
        ])
        questions = _analyze(profile)["screening_questions"]
        assert any("overlap" in q["question"].lower() for q in questions)


# ─── graceful degradation ─────────────────────────────────────────────────


class TestGracefulDegradation:
    def test_empty_profile_produces_honest_result(self):
        result = _analyze(None, "")
        assert result["snapshot"]["total_experience_months"] == 0
        assert result["strengths"] == []
        assert "could not be determined" in result["summary"]["text"].lower()

    def test_legacy_payload_without_metadata_survives(self):
        payload = _profile_json()
        del payload["metadata"]
        result = run_intel_analysis(payload, "")
        assert result["snapshot"]["experience_count"] == 0

    def test_malformed_payload_degrades_to_none(self):
        assert build_profile_from_dict({"summary": 12345, "skills": "nope"}) is None

    def test_raw_text_skills_counted_as_mentions(self):
        """Legacy rows without structured data still show honest mentions."""
        result = _analyze(None, raw_text="Skilled in Kubernetes and Terraform.")
        assert result["snapshot"]["skills_mentioned"] >= 2


# ─── job-contextual composition ───────────────────────────────────────────


class TestJobContextComposition:
    def test_context_reuses_fit_result(self):
        from app.services.screening.intel_engine import build_job_context

        fit = {
            "job_id": "j1",
            "job_title": "Platform Engineer",
            "requirements": [
                {"requirement": "Kubernetes", "status": "unknown"},
                {"requirement": "Python", "status": "match"},
                {"requirement": "Terraform", "status": "gap"},
            ],
            "experience_alignment": {
                "required_years": 4, "relevant_years": 3, "total_years": 6,
                "relevance_basis": "relevant_experience",
            },
            "overall": {"classification": "good_match", "score": 72},
        }
        ctx = build_job_context(fit)
        assert ctx["fit_classification"] == "good_match"
        assert ctx["requirement_unknown"] == ["Kubernetes"]
        assert ctx["requirement_gaps"] == ["Terraform"]
        assert ctx["relevant_years"] == 3
        assert any("kubernetes" in q["question"].lower()
                   for q in ctx["additional_questions"])
        # Neutral wording only.
        lowered = json.dumps(ctx).lower()
        assert "lacks" not in lowered


# ─── LLM polish contract (same strict JSON contract as Phase 2) ──────────


class TestIntelLLMPolishContract:
    @pytest.mark.asyncio
    async def test_polish_rejects_canned_fallback_text(self):
        import importlib

        client_module = importlib.import_module("app.ai_core.llm_client")
        from app.ai_core.llm_client import LLMResponse

        async def canned(*args, **kwargs):
            return LLMResponse(content="I can help generate reports.")

        saved = client_module.llm_client.chat
        client_module.llm_client.chat = canned
        try:
            service = CandidateIntelService.__new__(CandidateIntelService)
            polished = await service._polish_summary({
                "snapshot": {},
                "strengths": [], "evidence_gaps": [], "review_flags": [],
                "summary": {"text": "Deterministic summary."},
            })
        finally:
            client_module.llm_client.chat = saved
        assert polished is None

    @pytest.mark.asyncio
    async def test_polish_accepts_valid_json(self):
        import importlib

        client_module = importlib.import_module("app.ai_core.llm_client")
        from app.ai_core.llm_client import LLMResponse

        async def good(*args, **kwargs):
            return LLMResponse(content=json.dumps({
                "summary": "About 3 years of evidenced platform work; strongest areas Python.",
            }))

        saved = client_module.llm_client.chat
        client_module.llm_client.chat = good
        try:
            service = CandidateIntelService.__new__(CandidateIntelService)
            polished = await service._polish_summary({
                "snapshot": {"total_experience_years": 3},
                "strengths": [{"title": "Python"}],
                "evidence_gaps": [], "review_flags": [],
                "summary": {"text": "Deterministic summary."},
            })
        finally:
            client_module.llm_client.chat = saved
        assert polished is not None
        assert "python" in polished.lower()


# ─── persistence + authorization integration ──────────────────────────────


async def _ensure_role(session, name, description):
    from app.domain.models import Role

    repo = UserRepository(session)
    role = await repo.find_role_by_name(name)
    if not role:
        role = Role(name=name, description=description)
        session.add(role)
        await session.flush()
    return role


async def _setup_recruiter(client, session, suffix):
    hr_role = await _ensure_role(session, "hr", "HR user")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": f"HR {suffix}", "email": f"hr{suffix}@test.com",
              "password": "SecureP@ss123"},
    )
    user_id = uuid.UUID(resp.json()["id"])
    repo = UserRepository(session)
    await repo.assign_role(user_id, hr_role.id)
    session.expire_all()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": f"hr{suffix}@test.com", "password": "SecureP@ss123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user_id


async def _setup_second_recruiter(client, session, suffix):
    recruiter_role = await _ensure_role(session, "recruiter", "Recruiter")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": f"Rec {suffix}", "email": f"rec{suffix}@test.com",
              "password": "SecureP@ss123"},
    )
    user_id = uuid.UUID(resp.json()["id"])
    repo = UserRepository(session)
    await repo.assign_role(user_id, recruiter_role.id)
    session.expire_all()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": f"rec{suffix}@test.com", "password": "SecureP@ss123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user_id


async def _setup_candidate(client, session, suffix):
    await _ensure_role(session, "candidate", "Job applicant")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": f"Candidate {suffix}", "email": f"cand{suffix}@test.com",
              "password": "SecureP@ss123"},
    )
    user_id = uuid.UUID(resp.json()["id"])
    return user_id


async def _create_job(client, headers, suffix, **extra):
    payload = {
        "title": "Senior Python Backend Engineer",
        "company": "Acme Corp",
        "employment_type": "full_time",
        "location": "Remote",
        "status": "published",
        "required_skills": ["Python", "FastAPI", "Kubernetes"],
        "preferred_skills": ["Docker"],
        "experience_required": "4+ years",
        "description": (
            "Strong Python, FastAPI and PostgreSQL required. "
            "Docker and Kubernetes are preferred.\n"
            "Responsibilities:\n- Design and build REST APIs.\n"
        ),
        **extra,
    }
    resp = await client.post("/api/v1/recruiter/jobs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _attach_resume(session, candidate_id, profile_json, raw_text):
    from sqlalchemy import select

    from app.domain.models import CandidateProfile, ParsedResumeData, Resume

    existing = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == candidate_id)
    )
    profile_row = existing.scalar_one_or_none()
    if not profile_row:
        profile_row = CandidateProfile(user_id=candidate_id, current_role="Engineer")
        session.add(profile_row)
        await session.flush()

    resume = Resume(
        user_id=candidate_id,
        profile_id=profile_row.id,
        original_filename=f"{candidate_id}.pdf",
        storage_path=f"/tmp/{candidate_id}.pdf",
        file_size=1024,
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=uuid.uuid4().hex,
        status="parsed",
        is_primary=True,
        version=1,
    )
    session.add(resume)
    await session.flush()

    parsed = ParsedResumeData(
        resume_id=resume.id,
        raw_text=raw_text,
        parsed_json={"resume_profile": profile_json},
    )
    session.add(parsed)
    await session.flush()
    return resume


def _block_embeddings(monkeypatch):
    from app.rag import embeddings as emb_module

    monkeypatch.setattr(
        emb_module.embedding_service, "embed_query", lambda *a, **k: [], raising=False,
    )


@pytest.mark.asyncio
async def test_intel_endpoint_full_flow_and_cache(client, session, monkeypatch):
    """Owner gets grounded intel; second call is cached; no LLM needed."""
    _block_embeddings(monkeypatch)

    async def llm_down(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    import importlib

    client_module = importlib.import_module("app.ai_core.llm_client")
    monkeypatch.setattr(client_module.llm_client, "chat", llm_down)

    hr_headers, hr_id = await _setup_recruiter(client, session, "intA")
    cand_id = await _setup_candidate(client, session, "intB")
    job_id = await _create_job(client, hr_headers, "int")

    profile = _profile_json(
        summary="Backend engineer with 9+ years of experience.",
        skills=[_skill("Python", "Programming Language"), _skill("Rust", "Programming Language")],
        experience=[_experience_entry(is_current=False, start_date="2022-01",
                                      end_date="2024-01", duration_months=None)],
    )
    await _attach_resume(session, cand_id, profile, "Built async APIs with Python.")
    from app.domain.models import JobApplication

    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/candidates/{cand_id}/intelligence"
    first = await client.get(url, headers=hr_headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["cached"] is False
    assert body["candidate_name"].startswith("Candidate")
    assert body["engine_version"]
    assert body["summary"]["source"] == "deterministic"

    depths = {a["skill"]: a["depth"] for a in body["skill_assessments"]}
    assert depths.get("Python") in ("strong", "expert_level_evidence", "moderate")
    flags = [f["flag_type"] for f in body["review_flags"]]
    assert "stated_vs_timeline_mismatch" in flags
    questions = [q["question"] for q in body["screening_questions"]]
    assert questions

    second = await client.get(url, headers=hr_headers)
    assert second.status_code == 200
    assert second.json()["cached"] is True


@pytest.mark.asyncio
async def test_job_intel_composes_fit_context(client, session, monkeypatch):
    _block_embeddings(monkeypatch)

    async def llm_down(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    import importlib

    client_module = importlib.import_module("app.ai_core.llm_client")
    monkeypatch.setattr(client_module.llm_client, "chat", llm_down)

    hr_headers, _ = await _setup_recruiter(client, session, "jitA")
    cand_id = await _setup_candidate(client, session, "jitB")
    job_id = await _create_job(client, hr_headers, "jit")

    profile = _profile_json(
        skills=[_skill("Python", "Programming Language")],
        experience=[_experience_entry()],
    )
    await _attach_resume(session, cand_id, profile, "Built APIs with Python.")
    from app.domain.models import JobApplication

    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/intelligence"
    resp = await client.get(url, headers=hr_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    ctx = body["job_context"]
    assert ctx["job_id"] == job_id
    assert ctx["fit_classification"]
    # Kubernetes has no evidence in this resume → unknown/gap + question.
    combined = ctx["requirement_gaps"] + ctx["requirement_unknown"]
    assert any("kubernetes" in c.lower() for c in combined)
    assert ctx["additional_questions"]


@pytest.mark.asyncio
async def test_intel_blocks_unrelated_recruiter(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, hr_id = await _setup_recruiter(client, session, "isoA")
    intruder, other_id = await _setup_second_recruiter(client, session, "isoB")
    cand_id = await _setup_candidate(client, session, "isoC")
    job_id = await _create_job(client, hr_headers, "iso")

    profile = _profile_json()
    await _attach_resume(session, cand_id, profile, "")
    from app.domain.models import JobApplication

    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/candidates/{cand_id}/intelligence"
    forbidden = await client.get(url, headers=intruder)
    assert forbidden.status_code == 403

    job_url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/intelligence"
    forbidden_job = await client.get(job_url, headers=intruder)
    assert forbidden_job.status_code == 403


@pytest.mark.asyncio
async def test_intel_denies_candidate_role(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, _ = await _setup_recruiter(client, session, "roleA")
    cand_id = await _setup_candidate(client, session, "roleB")
    job_id = await _create_job(client, hr_headers, "role")
    from app.domain.models import JobApplication

    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "candroleB@test.com", "password": "SecureP@ss123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    url = f"/api/v1/screening/candidates/{cand_id}/intelligence"
    resp = await client.get(url, headers=headers)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_intel_without_resume_is_graceful(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, _ = await _setup_recruiter(client, session, "nresA")
    cand_id = await _setup_candidate(client, session, "nresB")
    job_id = await _create_job(client, hr_headers, "nres")
    from app.domain.models import JobApplication

    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/candidates/{cand_id}/intelligence"
    resp = await client.get(url, headers=hr_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["snapshot"]["total_experience_months"] == 0
    assert "could not be determined" in body["summary"]["text"].lower()


@pytest.mark.asyncio
async def test_intel_cache_invalidated_by_new_resume(client, session, monkeypatch):
    """Uploading a newer resume must invalidate the cached intelligence."""
    _block_embeddings(monkeypatch)

    async def llm_down(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    import importlib

    client_module = importlib.import_module("app.ai_core.llm_client")
    monkeypatch.setattr(client_module.llm_client, "chat", llm_down)

    hr_headers, _ = await _setup_recruiter(client, session, "freshA")
    cand_id = await _setup_candidate(client, session, "freshB")
    job_id = await _create_job(client, hr_headers, "fresh")

    profile_v1 = _profile_json(skills=[_skill("Python", "Programming Language")])
    resume = await _attach_resume(session, cand_id, profile_v1, "")
    from app.domain.models import JobApplication

    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/candidates/{cand_id}/intelligence"
    first = await client.get(url, headers=hr_headers)
    assert first.json()["cached"] is False
    second = await client.get(url, headers=hr_headers)
    assert second.json()["cached"] is True

    # Simulate a re-parse of the same resume (updated_at moves forward).
    from datetime import datetime, timedelta, timezone

    resume.updated_at = datetime.now(timezone.utc) + timedelta(seconds=5)
    session.add(resume)
    await session.flush()

    third = await client.get(url, headers=hr_headers)
    assert third.json()["cached"] is False


@pytest.mark.asyncio
async def test_legacy_parsed_row_self_heals_from_stored_file(
    client, session, monkeypatch, tmp_path,
):
    """Regression: pre-Phase-1 parsed rows (legacy flat dict, no
    ``resume_profile``) must be re-parsed from the stored file once and the
    structured profile written back — instead of degrading every skill to a
    raw-text mention."""
    _block_embeddings(monkeypatch)

    async def llm_down(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    import importlib

    client_module = importlib.import_module("app.ai_core.llm_client")
    monkeypatch.setattr(client_module.llm_client, "chat", llm_down)

    # Fake stored file so os.path.isfile() passes.
    fake_file = tmp_path / "resume.pdf"
    fake_file.write_bytes(b"%PDF-1.4 dummy")

    hr_headers, _ = await _setup_recruiter(client, session, "healA")
    cand_id = await _setup_candidate(client, session, "healB")
    job_id = await _create_job(client, hr_headers, "heal")

    structured = _profile_json(
        summary="Platform engineer.",
        skills=[_skill("Kubernetes", "DevOps")],
        experience=[_experience_entry(duration_months=30)],
    )

    from app.services.candidate.resume_parser.engine import ResumeIntelligenceEngine

    class FakeEngine:
        def __init__(self, file_path):
            pass

        def parse(self):
            profile = build_profile_from_dict(structured)
            return profile, {}

    monkeypatch.setattr(ResumeIntelligenceEngine, "__init__", FakeEngine.__init__)
    monkeypatch.setattr(ResumeIntelligenceEngine, "parse", FakeEngine.parse)

    from sqlalchemy import select

    from app.domain.models import (
        CandidateProfile,
        JobApplication,
        ParsedResumeData,
        Resume,
    )

    existing = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == cand_id)
    )
    profile_row = existing.scalar_one_or_none()
    if not profile_row:
        profile_row = CandidateProfile(user_id=cand_id, current_role="Engineer")
        session.add(profile_row)
        await session.flush()

    resume = Resume(
        user_id=cand_id,
        profile_id=profile_row.id,
        original_filename="legacy.pdf",
        storage_path=str(fake_file),
        file_size=1024,
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=uuid.uuid4().hex,
        status="parsed",
        is_primary=True,
        version=1,
    )
    session.add(resume)
    await session.flush()

    # Legacy flat parsed row: NO resume_profile key.
    parsed = ParsedResumeData(
        resume_id=resume.id,
        raw_text="Backend engineer. Skills: kubernetes.",
        parsed_json={"skills": ["kubernetes"], "language": "en"},
    )
    session.add(parsed)
    await session.flush()
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/candidates/{cand_id}/intelligence"
    resp = await client.get(url, headers=hr_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Structured evidence was recovered: the skill now has a structured
    # listing (confidence "low") instead of raw-text-only ("insufficient"),
    # and the timeline/snapshot reflect the parsed experience entry.
    k8s = next(
        a for a in body["skill_assessments"] if a["skill"].lower() == "kubernetes"
    )
    assert k8s["counts"]["skills_section"] == 1
    assert k8s["confidence"] == "low"
    assert body["snapshot"]["experience_count"] == 1
    assert body["snapshot"]["total_experience_years"] is not None

    # The backfilled profile was persisted for future runs.
    await session.refresh(parsed)
    assert (parsed.parsed_json or {}).get("resume_profile")


@pytest.mark.asyncio
async def test_legacy_row_without_file_stays_graceful(client, session, monkeypatch):
    """No stored file → self-heal is skipped; raw-text analysis still works."""
    _block_embeddings(monkeypatch)

    async def llm_down(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    import importlib

    client_module = importlib.import_module("app.ai_core.llm_client")
    monkeypatch.setattr(client_module.llm_client, "chat", llm_down)

    hr_headers, _ = await _setup_recruiter(client, session, "nofileA")
    cand_id = await _setup_candidate(client, session, "nofileB")
    job_id = await _create_job(client, hr_headers, "nofile")

    from sqlalchemy import select

    from app.domain.models import (
        CandidateProfile,
        JobApplication,
        ParsedResumeData,
        Resume,
    )

    existing = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == cand_id)
    )
    profile_row = existing.scalar_one_or_none()
    if not profile_row:
        profile_row = CandidateProfile(user_id=cand_id, current_role="Engineer")
        session.add(profile_row)
        await session.flush()

    resume = Resume(
        user_id=cand_id,
        profile_id=profile_row.id,
        original_filename="gone.pdf",
        storage_path=str(tmp_path_nonexistent()),
        file_size=1024,
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=uuid.uuid4().hex,
        status="parsed",
        is_primary=True,
        version=1,
    )
    session.add(resume)
    await session.flush()

    parsed = ParsedResumeData(
        resume_id=resume.id,
        raw_text="Experienced with Kubernetes operations.",
        parsed_json={"skills": ["kubernetes"]},
    )
    session.add(parsed)
    await session.flush()
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/candidates/{cand_id}/intelligence"
    resp = await client.get(url, headers=hr_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["snapshot"]["skills_mentioned"] >= 1
    assert body["skill_assessments"]


def tmp_path_nonexistent():
    import tempfile

    import os as _os

    return _os.path.join(tempfile.gettempdir(), f"missing-{uuid.uuid4().hex}.pdf")
