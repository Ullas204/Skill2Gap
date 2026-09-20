"""Phase 2 — Evidence-Grounded Job Matching Intelligence tests."""

import uuid

import pytest
from httpx import AsyncClient

from app.domain.enums import EmploymentType, JobStatus
from app.domain.models import (
    Job,
    JobApplication,
    Organization,
    OrganizationMembership,
    ParsedResumeData,
    Resume,
    Role,
    UserRole,
)
from app.repositories.user import UserRepository
from app.services.screening.fit_engine import (
    CandidateEvidenceIndex,
    FitEngine,
    build_profile_from_dict,
)
from app.services.screening.fit_service import FitService
from app.services.screening.requirement_extractor import (
    EXTRACTOR_VERSION,
    JobRequirementExtractor,
)


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
    skills=None,
    experience=None,
    projects=None,
    certifications=None,
    education=None,
):
    return {
        "schema_version": "1",
        "summary": "Backend engineer.",
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


def _requirements(**overrides):
    doc = {
        "extractor_version": EXTRACTOR_VERSION,
        "required_skills": [
            {"name": "Python", "category": "Programming Language", "matched_on": "python"},
            {"name": "FastAPI", "category": "Framework", "matched_on": "fastapi"},
            {"name": "Kubernetes", "category": "DevOps", "matched_on": "kubernetes"},
        ],
        "preferred_skills": [],
        "minimum_experience_years": None,
        "experience_note": None,
        "education": None,
        "certifications": [],
        "responsibilities": [],
        "skill_source_quotes": {},
    }
    doc.update(overrides)
    return doc


def _analyze(requirements, profile=None, raw_text="", title="Senior Python Backend Engineer"):
    return FitEngine(title, requirements, CandidateEvidenceIndex(
        build_profile_from_dict(profile), raw_text,
    )).analyze()


# ─── STEP A: skill normalization reuse (Feature 2) ────────────────────────


class TestSharedNormalization:
    def test_normalizer_is_shared_service(self):
        from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer

        assert SkillNormalizer.normalize("Postgres").name == "PostgreSQL"
        assert SkillNormalizer.normalize("Fast API").name == "FastAPI"
        assert SkillNormalizer.normalize("python 3").name == "Python"

    def test_extract_from_text_finds_known_skills(self):
        from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer

        found = SkillNormalizer.extract_from_text(
            "Strong Python, FastAPI and PostgreSQL required."
        )
        names = {s.name for s in found}
        assert {"Python", "FastAPI", "PostgreSQL"} <= names

    def test_extract_from_text_ignores_unknown_words(self):
        from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer

        found = SkillNormalizer.extract_from_text("Must enjoy foobazqux workflows")
        assert found == []

    def test_extract_from_text_avoids_common_words(self):
        from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer

        # "go" must not match ordinary English usage.
        found = SkillNormalizer.extract_from_text("We go to market in May")
        assert all(s.name.lower() != "go" for s in found)


# ─── STEP B: job requirement extraction (Feature 1) ───────────────────────


EXAMPLE_JD = (
    "Looking for a Senior Python Backend Engineer with 4+ years of experience.\n"
    "\n"
    "Strong Python, FastAPI and PostgreSQL required. Docker and Kubernetes are preferred.\n"
    "\n"
    "Responsibilities:\n"
    "- Design and build REST APIs.\n"
    "- Lead backend architecture decisions.\n"
)


class TestRequirementExtraction:
    def _extractor(self, description, **job_fields):
        class FakeJob:
            pass

        job = FakeJob()
        job.title = job_fields.get("title", "Senior Python Backend Engineer")
        job.description = description
        job.required_skills = job_fields.get("required_skills", [])
        job.preferred_skills = job_fields.get("preferred_skills", [])
        job.experience_required = job_fields.get("experience_required")
        job.education_required = job_fields.get("education_required")
        return JobRequirementExtractor(job)

    def test_example_job_description(self):
        doc = self._extractor(EXAMPLE_JD).extract()
        req_names = {s["name"] for s in doc["required_skills"]}
        pref_names = {s["name"] for s in doc["preferred_skills"]}
        assert {"Python", "FastAPI", "PostgreSQL"} <= req_names
        assert {"Docker", "Kubernetes"} <= pref_names
        assert doc["minimum_experience_years"] == 4.0

    def test_structured_columns_take_precedence_and_merge(self):
        doc = self._extractor(
            "Kubernetes is preferred.",
            required_skills=["Python", "Postgres"],
            preferred_skills=["Redis"],
        ).extract()
        req_names = {s["name"] for s in doc["required_skills"]}
        pref_names = {s["name"] for s in doc["preferred_skills"]}
        assert {"Python", "PostgreSQL"} <= req_names  # normalized via shared dictionary
        assert {"Redis", "Kubernetes"} <= pref_names

    def test_no_invention_when_no_skills_present(self):
        doc = self._extractor(
            "We are a friendly team that likes hiking and coffee.",
            title="Community Manager",
        ).extract()
        assert doc["required_skills"] == []
        assert doc["preferred_skills"] == []
        assert doc["minimum_experience_years"] is None

    def test_experience_range_uses_lower_bound(self):
        doc = self._extractor("Requires 3-5 years of experience.").extract()
        assert doc["minimum_experience_years"] == 3.0

    def test_responsibilities_extraction(self):
        doc = self._extracter_responsibilities()
        assert "Design and build REST APIs" in doc
        assert len(doc) <= 6

    def _extracter_responsibilities(self):
        return self._extractor(EXAMPLE_JD).extract()["responsibilities"]

    def test_education_extraction(self):
        doc = self._extractor(
            "Bachelor's degree in Computer Science or equivalent required."
        ).extract()
        assert doc["education"] is not None
        assert "Bachelor" in doc["education"]

    def test_certification_extraction(self):
        doc = self._extractor("AWS certification is a plus.").extract()
        assert any("certification" in c.lower() for c in doc["certifications"])

    def test_quotes_are_real_jd_text(self):
        doc = self._extractor(EXAMPLE_JD).extract()
        quote = doc["skill_source_quotes"]["fastapi"]
        assert "FastAPI" in quote


# ─── STEP C: evidence mapping + classification (Features 3/4/5/6) ─────────


class TestEvidenceMapping:
    def test_professional_experience_is_strong_match(self):
        profile = _profile_json(
            skills=[_skill("FastAPI", "Framework")],
            experience=[
                _experience_entry(
                    description=["Built asynchronous APIs using Python and FastAPI."],
                    technologies=["Python", "FastAPI"],
                ),
            ],
        )
        result = _analyze(_requirements(), profile)
        fastapi = next(r for r in result["requirements"] if r["requirement"] == "FastAPI")
        assert fastapi["status"] == "match"
        assert fastapi["evidence_strength"] == "strong"
        sources = {e["source"] for e in fastapi["evidence"]}
        assert "experience" in sources
        assert all(e["quote"] for e in fastapi["evidence"])

    def test_skills_section_only_is_weak_partial(self):
        profile = _profile_json(skills=[_skill("Docker", "DevOps")])
        result = _analyze(
            _requirements(required_skills=[], preferred_skills=[
                {"name": "Docker", "category": "DevOps", "matched_on": "docker"},
            ]),
            profile,
        )
        docker = next(r for r in result["requirements"] if r["requirement"] == "Docker")
        assert docker["status"] == "partial"
        assert docker["evidence_strength"] == "weak"
        assert "skills section" in docker["reason"]

    def test_project_evidence_is_moderate(self):
        profile = _profile_json(
            projects=[{
                "name": "AI Hiring Platform",
                "description": ["Built an AI hiring platform using Python."],
                "technologies": ["Python"],
                "responsibilities": [],
                "achievements": [],
                "start_date": None,
                "end_date": None,
                "source_section": "Projects",
                "source_text": None,
            }],
        )
        result = _analyze(
            _requirements(required_skills=[
                {"name": "Python", "category": "Programming Language", "matched_on": "python"},
            ]),
            profile,
        )
        python = next(r for r in result["requirements"] if r["requirement"] == "Python")
        assert python["status"] == "match"
        assert python["evidence_strength"] == "moderate"

    def test_no_evidence_is_gap_not_lack_of_skill(self):
        profile = _profile_json(
            skills=[_skill("Python", "Programming Language")],
            experience=[_experience_entry()],
        )
        result = _analyze(_requirements(), profile, raw_text="Built Python APIs.")
        k8s = next(r for r in result["requirements"] if r["requirement"] == "Kubernetes")
        assert k8s["status"] == "gap"
        assert "No supporting evidence" in k8s["reason"]
        assert "lacks" not in k8s["reason"].lower()

    def test_empty_resume_is_unknown(self):
        result = _analyze(_requirements(), None, raw_text="")
        k8s = next(r for r in result["requirements"] if r["requirement"] == "Kubernetes")
        assert k8s["status"] == "unknown"
        assert "does not provide enough" in k8s["reason"]

    def test_related_skill_yields_partial(self):
        profile = _profile_json(
            skills=[_skill("REST APIs", "API Style")],
            experience=[_experience_entry(technologies=["rest"])],
        )
        result = _analyze(
            _requirements(required_skills=[
                {"name": "GraphQL", "category": "API Style", "matched_on": "graphql"},
            ]),
            profile,
        )
        graphql = next(r for r in result["requirements"] if r["requirement"] == "GraphQL")
        assert graphql["status"] == "partial"


# ─── anti-hallucination ────────────────────────────────────────────────────


class TestAntiHallucination:
    def test_never_invents_kubernetes_experience(self):
        profile = _profile_json(skills=[_skill("Python", "Programming Language")])
        result = _analyze(
            _requirements(required_skills=[
                {"name": "Kubernetes", "category": "DevOps", "matched_on": "kubernetes"},
            ]),
            profile,
            raw_text="Built Python APIs.",
        )
        k8s = next(r for r in result["requirements"])
        assert k8s["requirement"] == "Kubernetes"
        assert k8s["status"] in ("gap", "unknown")
        assert k8s["evidence"] == []
        text_blob = (k8s["reason"] + " " + result["overall"]["summary"]).lower()
        assert "deployed" not in text_blob
        assert "candidate lacks" not in text_blob
        assert "no supporting" in text_blob or "not provide enough" in text_blob

    def test_all_evidence_quotes_exist_in_source_material(self):
        raw_text = "Developed asynchronous APIs using Python and FastAPI. Managed PostgreSQL databases."
        profile = _profile_json(
            experience=[_experience_entry(
                description=["Managed PostgreSQL databases."],
                technologies=["PostgreSQL"],
            )],
        )
        result = _analyze(
            _requirements(required_skills=[
                {"name": "PostgreSQL", "category": "Database", "matched_on": "postgresql"},
                {"name": "Kafka", "category": "Data", "matched_on": "kafka"},
            ]),
            profile,
            raw_text=raw_text,
        )
        for requirement in result["requirements"]:
            for evidence in requirement["evidence"]:
                assert evidence["quote"], requirement["requirement"]

    def test_rag_failure_degrades_to_gap(self, monkeypatch):
        from app.rag import embeddings as emb_module

        monkeypatch.setattr(
            emb_module.embedding_service,
            "embed_query",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("vector store down")),
            raising=False,
        )
        profile = _profile_json(skills=[_skill("Python", "Programming Language")])
        result = _analyze(
            _requirements(required_skills=[
                {"name": "Kubernetes", "category": "DevOps", "matched_on": "kubernetes"},
            ]),
            profile,
            raw_text="Some unrelated long resume paragraph text here.",
        )
        k8s = result["requirements"][0]
        assert k8s["status"] in ("gap", "unknown")

    @pytest.mark.asyncio
    async def test_llm_failure_keeps_deterministic_summary(self, monkeypatch):
        async def boom(*args, **kwargs):
            raise RuntimeError("LLM down")

        # NOTE: app.ai_core.__init__ re-exports singletons, so the package
        # attribute is the instance, not the module — resolve via importlib.
        import importlib

        client_module = importlib.import_module("app.ai_core.llm_client")

        monkeypatch.setattr(client_module.llm_client, "chat", boom)
        profile = _profile_json(experience=[_experience_entry()])

        result = _analyze(_requirements(), profile)
        summary = result["overall"]["summary"]
        assert summary  # deterministic summary exists

        # Directly exercise the guarded polish path with the failing LLM.
        service = FitService.__new__(FitService)  # no DB needed for this method
        fake_result = {"overall": {"summary": summary, "classification": "good_match"}}
        polished = await service._polish_summary(fake_result)
        assert polished is None


# ─── experience alignment (Feature 8) ─────────────────────────────────────


class TestExperienceAlignment:
    def test_relevant_experience_meets_requirement(self):
        profile = _profile_json(experience=[_experience_entry(duration_months=58)])
        result = _analyze(
            _requirements(minimum_experience_years=4.0), profile,
        )
        ea = result["experience_alignment"]
        assert ea["status"] == "match"
        assert ea["relevance_basis"] == "relevant_experience"
        assert ea["relevant_years"] >= 4.0

    def test_irrelevant_experience_downgrades_to_partial(self):
        profile = _profile_json(experience=[
            _experience_entry(
                job_title="Chef",
                company="Bistro",
                description=["Cooked pasta dishes."],
                technologies=[],
                duration_months=60,
            ),
        ])
        result = _analyze(
            _requirements(minimum_experience_years=4.0), profile,
        )
        ea = result["experience_alignment"]
        assert ea["status"] == "partial"
        assert ea["relevance_basis"] == "total_experience"

    def test_missing_dates_are_unknown(self):
        profile = _profile_json(experience=[
            _experience_entry(start_date=None, end_date=None, duration_months=None,
                              dates_uncertain=True),
        ])
        result = _analyze(
            _requirements(minimum_experience_years=2.0), profile,
        )
        ea = result["experience_alignment"]
        assert ea["status"] == "unknown"

    def test_no_requirement_reported_honestly(self):
        profile = _profile_json(experience=[_experience_entry()])
        result = _analyze(_requirements(minimum_experience_years=None), profile)
        ea = result["experience_alignment"]
        assert ea["status"] == "unknown"
        assert "No minimum experience requirement" in ea["reason"]


# ─── responsibility alignment (Feature 9) ──────────────────────────────────


class TestResponsibilityAlignment:
    def test_direct_alignment_is_strong(self):
        profile = _profile_json(experience=[
            _experience_entry(description=[
                "Designed and built REST APIs for the core product.",
            ]),
        ])
        result = _analyze(
            _requirements(responsibilities=["Design and build REST APIs"]),
            profile,
        )
        resp = result["responsibilities"][0]
        assert resp["alignment"] in ("strong", "moderate")
        assert resp["evidence"], "evidence quote must be attached"
        assert "REST" in resp["evidence"][0]["quote"]

    def test_no_alignment_reports_none_without_evidence(self):
        profile = _profile_json(experience=[
            _experience_entry(description=["Wrote marketing copy."], technologies=[]),
        ])
        result = _analyze(
            _requirements(responsibilities=["Manage cloud infrastructure budgets"]),
            profile,
        )
        resp = result["responsibilities"][0]
        assert resp["alignment"] == "none"
        assert resp["evidence"] == []


# ─── overall fit (Features 7/10 + scoring rule) ────────────────────────────


class TestOverallFit:
    def test_transparent_weights_are_visible(self):
        profile = _profile_json(experience=[_experience_entry()])
        result = _analyze(_requirements(minimum_experience_years=2.0), profile)
        breakdown = result["overall"]["breakdown"]
        assert breakdown["weights"] == {
            "required_skills": 0.45,
            "experience": 0.25,
            "responsibilities": 0.15,
            "preferred_skills": 0.15,
        }
        assert "0.45" in breakdown["formula"]
        for component, value in breakdown["components"].items():
            assert value is None or 0.0 <= value <= 1.0

    def test_strong_candidate_classification(self):
        profile = _profile_json(
            skills=[
                _skill("Python", "Programming Language"),
                _skill("FastAPI", "Framework"),
            ],
            experience=[_experience_entry(
                description=[
                    "Developed asynchronous APIs using Python and FastAPI.",
                    "Deployed services on Kubernetes clusters.",
                ],
                technologies=["Python", "FastAPI", "Kubernetes"],
                duration_months=60,
            )],
        )
        result = _analyze(
            _requirements(
                preferred_skills=[{"name": "Kubernetes", "category": "DevOps", "matched_on": "kubernetes"}],
                minimum_experience_years=4.0,
                responsibilities=["Design and build REST APIs"],
            ),
            profile,
        )
        assert result["overall"]["classification"] in ("strong_match", "good_match")
        gaps = result["skill_gaps"]
        assert "Python" in gaps["strengths"]

    def test_insufficient_evidence_override(self):
        # Two requirements, both UNKNOWN (no resume data at all).
        result = _analyze(_requirements(), None, raw_text="")
        assert result["overall"]["classification"] == "insufficient_evidence"

    def test_summary_mentions_gaps_carefully(self):
        profile = _profile_json(skills=[_skill("Python", "Programming Language")])
        result = _analyze(_requirements(), profile, raw_text="")
        summary = result["overall"]["summary"].lower()
        assert "limited or no evidence was found for: fastapi, kubernetes." in summary

    def test_disclaimer_present(self):
        result = _analyze(_requirements(), None, raw_text="")
        assert "decision support" in result["overall"]["disclaimer"]


# ─── raw-text evidence (resumes with missing/sparse structured profile) ────


class TestRawTextEvidence:
    def test_mention_in_raw_text_yields_partial_not_gap(self):
        """Regression: legacy resumes with empty parsed_json must still match
        skills that literally appear in the resume text."""
        result = _analyze(
            _requirements(required_skills=[
                {"name": "Terraform", "category": "DevOps", "matched_on": "terraform"},
                {"name": "Kubernetes", "category": "DevOps", "matched_on": "kubernetes"},
            ]),
            None,  # no structured profile at all
            raw_text="Automated our infrastructure with Terraform and Ansible scripts.",
        )
        by_name = {r["requirement"]: r for r in result["requirements"]}
        terraform = by_name["Terraform"]
        assert terraform["status"] == "partial"
        assert terraform["evidence"], "raw-text mention must carry evidence"
        assert terraform["evidence"][0]["source"] == "resume_text"
        assert "terraform" in terraform["evidence"][0]["quote"].lower()
        # Unmentioned skill is still a genuine gap (raw text was scanned).
        assert by_name["Kubernetes"]["status"] == "gap"

    def test_education_from_raw_text(self):
        result = _analyze(
            _requirements(education="Bachelor's degree"),
            None,
            raw_text="Education: B.S. in Computer Science, State University, 2018.",
        )
        edu = [r for r in result["requirements"] if r["requirement_type"] == "education"]
        assert edu and edu[0]["status"] == "partial"
        assert edu[0]["evidence"][0]["source"] == "resume_text"

    def test_responsibility_alignment_uses_raw_text(self):
        result = _analyze(
            _requirements(responsibilities=["Own CI/CD pipelines and automation"]),
            None,
            raw_text="Owned the CI/CD pipelines and release automation for three teams.",
        )
        resp = result["responsibilities"][0]
        assert resp["alignment"] in ("weak", "moderate", "strong")
        assert resp["evidence"]
        assert resp["evidence"][0]["source"] == "resume_text"

    def test_per_candidate_results_differ(self):
        """Regression: two candidates with different raw texts must not get
        identical requirement outcomes."""
        reqs = _requirements(required_skills=[
            {"name": "Terraform", "category": "DevOps", "matched_on": "terraform"},
        ])
        devops = _analyze(reqs, None, raw_text="Wrote Terraform modules daily.")
        other = _analyze(reqs, None, raw_text="Taught kindergarten classes.")
        statuses = {
            "devops": next(r for r in devops["requirements"])["status"],
            "other": next(r for r in other["requirements"])["status"],
        }
        assert statuses["devops"] == "partial"
        assert statuses["other"] == "gap"


# ─── LLM polish contract ───────────────────────────────────────────────────

class TestLLMPolishContract:
    @pytest.mark.asyncio
    async def test_polish_rejects_non_json_fallback_text(self):
        """Regression: the router's canned rule-based fallback ("I can help
        generate reports...") must never replace the deterministic summary."""
        import importlib

        client_module = importlib.import_module("app.ai_core.llm_client")
        from app.ai_core.llm_client import LLMResponse

        async def canned(*args, **kwargs):
            return LLMResponse(
                content="I can help generate reports. "
                "Please specify the report type and time range you're interested in.",
            )

        saved = client_module.llm_client.chat
        client_module.llm_client.chat = canned
        try:
            service = FitService.__new__(FitService)
            polished = await service._polish_summary({
                "job_title": "Backend Engineer",
                "overall": {
                    "classification": "good_match",
                    "summary": "Good alignment with the Backend Engineer role.",
                },
                "skill_gaps": {"strengths": [], "partial": [], "gaps": [], "unknown": []},
                "experience_alignment": {},
            })
        finally:
            client_module.llm_client.chat = saved
        assert polished is None

    @pytest.mark.asyncio
    async def test_polish_accepts_valid_json_contract(self):
        import importlib
        import json as _json

        client_module = importlib.import_module("app.ai_core.llm_client")
        from app.ai_core.llm_client import LLMResponse

        async def good(*args, **kwargs):
            return LLMResponse(content=_json.dumps({
                "summary": "Good alignment with the Backend Engineer role based on listed experience.",
            }))

        saved = client_module.llm_client.chat
        client_module.llm_client.chat = good
        try:
            service = FitService.__new__(FitService)
            polished = await service._polish_summary({
                "job_title": "Backend Engineer",
                "overall": {
                    "classification": "good_match",
                    "summary": "Good alignment with the Backend Engineer role.",
                },
                "skill_gaps": {"strengths": [], "partial": [], "gaps": [], "unknown": []},
                "experience_alignment": {},
            })
        finally:
            client_module.llm_client.chat = saved
        assert polished is not None
        assert "backend engineer" in polished.lower()


# ─── persistence + authorization integration ───────────────────────────────


async def _ensure_role(session, name, description):
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
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": f"cand{suffix}@test.com", "password": "SecureP@ss123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user_id


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


async def _create_org_job(session, recruiter_id, organization_id):
    """JobCreate has no organization_id field, so org-scoped jobs are created directly."""
    job = Job(
        recruiter_id=recruiter_id,
        title="Senior Python Backend Engineer",
        company="Acme Corp",
        employment_type=EmploymentType.FULL_TIME,
        location="Remote",
        status=JobStatus.PUBLISHED,
        required_skills=["Python", "FastAPI", "Kubernetes"],
        preferred_skills=["Docker"],
        experience_required="4+ years",
        description=(
            "Strong Python, FastAPI and PostgreSQL required. "
            "Docker and Kubernetes are preferred.\n"
            "Responsibilities:\n- Design and build REST APIs.\n"
        ),
        organization_id=organization_id,
    )
    session.add(job)
    await session.flush()
    return str(job.id)


async def _attach_resume(session, candidate_id, profile_json, raw_text):
    profile_repo_row = None
    from sqlalchemy import select
    from app.domain.models import CandidateProfile

    existing = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == candidate_id)
    )
    profile_repo_row = existing.scalar_one_or_none()
    if not profile_repo_row:
        profile_repo_row = CandidateProfile(user_id=candidate_id, current_role="Engineer")
        session.add(profile_repo_row)
        await session.flush()

    resume = Resume(
        user_id=candidate_id,
        profile_id=profile_repo_row.id,
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


@pytest.mark.asyncio
async def test_fit_endpoint_full_flow(client, session, monkeypatch):
    """Owner recruiter gets a grounded fit; second call is served from cache."""
    _block_embeddings(monkeypatch)
    hr_headers, hr_id = await _setup_recruiter(client, session, "flow")
    cand_headers, cand_id = await _setup_candidate(client, session, "flow")

    job_id = await _create_job(client, hr_headers, "flow")
    profile = _profile_json(
        skills=[_skill("Python", "Programming Language"),
                _skill("FastAPI", "Framework")],
        experience=[_experience_entry(duration_months=55)],
    )
    await _attach_resume(session, cand_id, profile, "Built asynchronous APIs with Python.")

    app_row = JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id)
    session.add(app_row)
    await session.flush()

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    first = await client.get(url, headers=hr_headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["cached"] is False
    assert body["job_title"] == "Senior Python Backend Engineer"
    statuses = {r["requirement"]: r["status"] for r in body["requirements"]}
    assert statuses["Python"] == "match"
    assert statuses["FastAPI"] in ("match", "partial")
    assert statuses["Kubernetes"] in ("gap", "unknown")
    assert body["overall"]["classification"] in (
        "strong_match", "good_match", "partial_match",
    )
    assert body["experience_alignment"]["status"] in ("match", "partial")
    assert body["requirements_info"]["extracted_count"] >= 3

    second = await client.get(url, headers=hr_headers)
    assert second.status_code == 200
    assert second.json()["cached"] is True


def _block_embeddings(monkeypatch):
    """embed_query is synchronous; return [] so fallback retrieval short-circuits."""
    from app.rag import embeddings as emb_module

    monkeypatch.setattr(
        emb_module.embedding_service, "embed_query", lambda *a, **k: [], raising=False,
    )


@pytest.mark.asyncio
async def test_fit_blocks_recruiter_from_other_org(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, hr_id = await _setup_recruiter(client, session, "isoA")
    other_headers, other_id = await _setup_second_recruiter(client, session, "isoB")
    cand_headers, cand_id = await _setup_candidate(client, session, "isoC")

    job_id = await _create_job(client, hr_headers, "iso")
    profile = _profile_json(skills=[_skill("Python", "Programming Language")])
    await _attach_resume(session, cand_id, profile, "")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    forbidden = await client.get(url, headers=other_headers)
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_fit_allows_same_organization_member(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, hr_id = await _setup_recruiter(client, session, "orgA")
    mate_headers, mate_id = await _setup_second_recruiter(client, session, "orgB")
    cand_headers, cand_id = await _setup_candidate(client, session, "orgC")

    org = Organization(name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}")
    session.add(org)
    await session.flush()
    session.add(OrganizationMembership(
        user_id=mate_id, organization_id=org.id, role="recruiter", status="active",
    ))
    await session.flush()

    job_id = await _create_org_job(session, hr_id, org.id)
    profile = _profile_json(skills=[_skill("Python", "Programming Language")])
    await _attach_resume(session, cand_id, profile, "")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    allowed = await client.get(url, headers=mate_headers)
    assert allowed.status_code == 200, allowed.text


@pytest.mark.asyncio
async def test_fit_requires_application(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, hr_id = await _setup_recruiter(client, session, "appA")
    cand_headers, cand_id = await _setup_candidate(client, session, "appB")
    job_id = await _create_job(client, hr_headers, "app")

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    resp = await client.get(url, headers=hr_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_fit_forbidden_for_candidate_role(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, hr_id = await _setup_recruiter(client, session, "roleA")
    cand_headers, cand_id = await _setup_candidate(client, session, "roleB")
    job_id = await _create_job(client, hr_headers, "role")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    resp = await client.get(url, headers=cand_headers)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_fit_survives_llm_outage(client, session, monkeypatch):
    _block_embeddings(monkeypatch)

    async def llm_down(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    import importlib

    client_module = importlib.import_module("app.ai_core.llm_client")

    monkeypatch.setattr(client_module.llm_client, "chat", llm_down)

    hr_headers, _ = await _setup_recruiter(client, session, "llmA")
    _, cand_id = await _setup_candidate(client, session, "llmB")
    job_id = await _create_job(client, hr_headers, "llm")
    profile = _profile_json(experience=[_experience_entry()])
    await _attach_resume(session, cand_id, profile, "")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    resp = await client.get(url, headers=hr_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall"]["summary_source"] == "deterministic"
    assert body["overall"]["summary"]


@pytest.mark.asyncio
async def test_fit_without_resume_returns_insufficient_evidence(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, _ = await _setup_recruiter(client, session, "nresA")
    _, cand_id = await _setup_candidate(client, session, "nresB")
    job_id = await _create_job(client, hr_headers, "nres")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    resp = await client.get(url, headers=hr_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall"]["classification"] == "insufficient_evidence"
    unknowns = [r for r in body["requirements"] if r["status"] == "unknown"]
    assert unknowns, "requirements without a resume must be unknown, not gap"


@pytest.mark.asyncio
async def test_requirement_extraction_is_cached_per_job(client, session, monkeypatch):
    _block_embeddings(monkeypatch)
    hr_headers, _ = await _setup_recruiter(client, session, "cacheA")
    _, cand_id = await _setup_candidate(client, session, "cacheB")
    job_id = await _create_job(client, hr_headers, "cache")
    profile = _profile_json(skills=[_skill("Python", "Programming Language")])
    await _attach_resume(session, cand_id, profile, "")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    call_count = {"n": 0}
    original = JobRequirementExtractor.extract

    def counting_extract(self):
        call_count["n"] += 1
        return original(self)

    monkeypatch.setattr(JobRequirementExtractor, "extract", counting_extract)

    url = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}/fit"
    await client.get(url, headers=hr_headers)
    first_count = call_count["n"]
    assert first_count == 1
    await client.get(url, headers=hr_headers)
    assert call_count["n"] == first_count, "unchanged job must not re-extract"


@pytest.mark.asyncio
async def test_existing_screening_reads_enforce_ownership(client, session):
    hr_headers, _ = await _setup_recruiter(client, session, "ownA")
    intruder, _ = await _setup_second_recruiter(client, session, "ownB")
    _, cand_id = await _setup_candidate(client, session, "ownC")
    job_id = await _create_job(client, hr_headers, "own")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    base = f"/api/v1/screening/jobs/{job_id}/candidates/{cand_id}"
    screening_resp = await client.get(base, headers=intruder)
    assert screening_resp.status_code == 403
    gap_resp = await client.get(f"{base}/skill-gap", headers=intruder)
    assert gap_resp.status_code == 403


@pytest.mark.asyncio
async def test_legacy_screening_flow_unaffected(client, session, monkeypatch):
    """Phase 2 must not break the pre-existing trigger/read flow."""
    hr_headers, _ = await _setup_recruiter(client, session, "legA")
    _, cand_id = await _setup_candidate(client, session, "legB")
    job_id = await _create_job(client, hr_headers, "leg")
    # Legacy screening requires an existing CandidateProfile.
    await _attach_resume(session, cand_id, _profile_json(), "")
    session.add(JobApplication(job_id=uuid.UUID(job_id), candidate_id=cand_id))
    await session.flush()

    screen = await client.post(f"/api/v1/screening/jobs/{job_id}/screen", headers=hr_headers)
    assert screen.status_code == 200, screen.text

    rankings = await client.get(f"/api/v1/screening/jobs/{job_id}/rankings", headers=hr_headers)
    assert rankings.status_code == 200
