import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import uuid

from app.services.screening.matching_engine import MatchingEngine
from app.services.screening.skill_gap import SkillGapAnalyzer


# ─── MatchingEngine Unit Tests ────────────────────────────────────────


class TestNormalizeSkill:
    def test_lowercase(self):
        assert MatchingEngine.normalize_skill("Python") == "python"

    def test_strips_whitespace(self):
        assert MatchingEngine.normalize_skill("  Machine Learning  ") == "machine learning"

    def test_replaces_hyphens(self):
        assert MatchingEngine.normalize_skill("ci-cd") == "ci cd"

    def test_replaces_underscores(self):
        assert MatchingEngine.normalize_skill("node_js") == "node js"


class TestSkillMatches:
    def test_exact_match(self):
        assert MatchingEngine.skill_matches("python", "python") is True

    def test_partial_match(self):
        assert MatchingEngine.skill_matches("react.js", "react") is True

    def test_synonym_match(self):
        assert MatchingEngine.skill_matches("ts", "typescript") is True

    def test_no_match(self):
        assert MatchingEngine.skill_matches("java", "python") is False

    def test_synonym_golang(self):
        assert MatchingEngine.skill_matches("golang", "go") is True

    def test_synonym_k8s(self):
        assert MatchingEngine.skill_matches("k8s", "kubernetes") is True

    def test_csharp_variant(self):
        assert MatchingEngine.skill_matches("c sharp", "c#") is True


class TestCalculateSkillMatch:
    def test_all_required_matched(self):
        score, matched, missing_req, missing_pref = MatchingEngine.calculate_skill_match(
            ["python", "react", "sql"], ["python", "react", "sql"]
        )
        assert score >= 80
        assert len(missing_req) == 0

    def test_some_missing_required(self):
        score, matched, missing_req, missing_pref = MatchingEngine.calculate_skill_match(
            ["python"], ["python", "java", "go"]
        )
        assert len(missing_req) == 2
        assert "java" in missing_req

    def test_no_skills_no_requirements(self):
        score, matched, missing_req, missing_pref = MatchingEngine.calculate_skill_match([], [])
        assert score == 100

    def test_preferred_skills_bonus(self):
        score_with, _, _, _ = MatchingEngine.calculate_skill_match(
            ["python", "react"], ["python"], ["react"]
        )
        score_without, _, _, _ = MatchingEngine.calculate_skill_match(
            ["python"], ["python"], ["react"]
        )
        assert score_with >= score_without


class TestCalculateExperienceMatch:
    def test_meets_requirement(self):
        assert MatchingEngine.calculate_experience_match(5, "3+ years") == 100

    def test_no_requirement(self):
        assert MatchingEngine.calculate_experience_match(3, None) == 80

    def test_below_requirement_close(self):
        score = MatchingEngine.calculate_experience_match(3, "4+ years")
        assert score in (85, 60)

    def test_far_below(self):
        assert MatchingEngine.calculate_experience_match(1, "5+ years") == 20


class TestCalculateEducationMatch:
    def test_meets_requirement(self):
        assert MatchingEngine.calculate_education_match(["B.Sc Computer Science"], "Bachelor") == 100

    def test_exceeds_requirement(self):
        assert MatchingEngine.calculate_education_match(["M.Sc AI"], "Bachelor") == 100

    def test_no_requirement(self):
        assert MatchingEngine.calculate_education_match(["B.Sc"], None) == 80

    def test_no_candidate_education(self):
        assert MatchingEngine.calculate_education_match([], "Bachelor") == 20


class TestCalculateProjectMatch:
    def test_no_projects(self):
        assert MatchingEngine.calculate_project_match(0, [], []) == 10

    def test_projects_with_tech_overlap(self):
        score = MatchingEngine.calculate_project_match(3, ["python", "react"], ["python", "sql"])
        assert score > 50

    def test_projects_no_overlap(self):
        score = MatchingEngine.calculate_project_match(2, ["java"], ["python"])
        assert score <= 60


class TestCalculateLocationMatch:
    def test_remote_job(self):
        assert MatchingEngine.calculate_location_match("New York, USA", "Remote") == 100

    def test_same_city(self):
        assert MatchingEngine.calculate_location_match("New York, USA", "New York, USA") == 100

    def test_same_country(self):
        score = MatchingEngine.calculate_location_match("New York, USA", "San Francisco, USA")
        assert score == 70

    def test_different_country(self):
        score = MatchingEngine.calculate_location_match("London, UK", "New York, USA")
        assert score == 30

    def test_no_candidate_location(self):
        assert MatchingEngine.calculate_location_match(None, "New York") == 60


class TestCalculateEmploymentTypeMatch:
    def test_matching(self):
        assert MatchingEngine.calculate_employment_type_match("full-time", "full-time") == 100

    def test_no_preference(self):
        assert MatchingEngine.calculate_employment_type_match(None, "full-time") == 70

    def test_mismatch(self):
        assert MatchingEngine.calculate_employment_type_match("part-time", "full-time") == 40


class TestSemanticSimilarity:
    def test_identical_text(self):
        score = MatchingEngine.calculate_semantic_similarity("python developer", "python developer")
        assert score >= 90

    def test_empty_text(self):
        score = MatchingEngine.calculate_semantic_similarity("", "hello")
        assert score == 30

    def test_similar_text(self):
        score = MatchingEngine.calculate_semantic_similarity(
            "python backend developer with experience in building apis",
            "experienced python backend engineer building rest apis",
        )
        assert score > 20


class TestOverallScore:
    def test_default_weights(self):
        score = MatchingEngine.calculate_overall_score(
            skill=100, experience=100, education=100,
            project=100, certification=100, location=100,
            employment_type=100, semantic=100,
        )
        assert score == 100

    def test_zero_scores(self):
        score = MatchingEngine.calculate_overall_score(
            skill=0, experience=0, education=0,
            project=0, certification=0, location=0,
            employment_type=0, semantic=0,
        )
        assert score == 0

    def test_custom_weights(self):
        score = MatchingEngine.calculate_overall_score(
            skill=100, experience=0, education=0,
            project=0, certification=0, location=0,
            employment_type=0, semantic=0,
            weights={"skills": 1.0, "experience": 0, "education": 0,
                      "projects": 0, "certifications": 0, "location": 0,
                      "employment_type": 0, "semantic": 0},
        )
        assert score == 100


class TestStrengthWeaknessRecommendation:
    def test_strong_candidate(self):
        scores = {"skill": 90, "experience": 85, "education": 80, "project": 75, "certification": 70, "semantic": 65}
        strengths = MatchingEngine.identify_strengths(scores, ["python", "react", "sql", "java", "go", "aws"])
        assert len(strengths) >= 3

    def test_weak_candidate(self):
        scores = {"skill": 30, "experience": 20, "education": 30, "project": 10, "certification": 10, "semantic": 20}
        weaknesses = MatchingEngine.identify_weaknesses(scores, ["python", "java"], ["react"])
        assert len(weaknesses) >= 2

    def test_recommendation_strongly(self):
        assert MatchingEngine.determine_recommendation(85) == "strongly_recommend"

    def test_recommendation_recommend(self):
        assert MatchingEngine.determine_recommendation(70) == "recommend"

    def test_recommendation_consider(self):
        assert MatchingEngine.determine_recommendation(50) == "consider"

    def test_recommendation_not_recommended(self):
        assert MatchingEngine.determine_recommendation(30) == "not_recommended"

    def test_strength_level_excellent(self):
        assert MatchingEngine.determine_strength_level(85) == "excellent"

    def test_strength_level_low(self):
        assert MatchingEngine.determine_strength_level(25) == "low"


# ─── SkillGapAnalyzer Unit Tests ─────────────────────────────────────


class TestSkillGapAnalyzer:
    def test_analyze_with_gaps(self):
        result = SkillGapAnalyzer.analyze(
            matched_skills=["python"],
            missing_required=["java", "go"],
            missing_preferred=["react"],
            candidate_experience_years=2,
            required_experience_str="5+ years",
            candidate_degrees=["B.Sc"],
            required_education="Master",
            candidate_certs=[],
            overall_score=45,
        )
        assert "java" in result["missing_required_skills"]
        assert "react" in result["missing_preferred_skills"]
        assert result["experience_gap_description"] is not None
        assert result["education_gap_description"] is not None
        assert result["interview_readiness_score"] < 60

    def test_analyze_strong_candidate(self):
        result = SkillGapAnalyzer.analyze(
            matched_skills=["python", "react", "sql", "java", "go"],
            missing_required=[],
            missing_preferred=[],
            candidate_experience_years=8,
            required_experience_str="5+ years",
            candidate_degrees=["M.Sc Computer Science"],
            required_education="Bachelor",
            candidate_certs=["AWS Solutions Architect"],
            overall_score=90,
        )
        assert len(result["missing_required_skills"]) == 0
        assert result["experience_gap_description"] is None
        assert result["education_gap_description"] is None
        assert result["interview_readiness_score"] >= 80

    def test_experience_gap_no_requirement(self):
        gap = SkillGapAnalyzer._experience_gap(3, None)
        assert gap is None

    def test_experience_gap_met(self):
        gap = SkillGapAnalyzer._experience_gap(5, "3+ years")
        assert gap is None

    def test_education_gap_no_requirement(self):
        gap = SkillGapAnalyzer._education_gap(["B.Sc"], None)
        assert gap is None

    def test_education_gap_no_candidate_education(self):
        gap = SkillGapAnalyzer._education_gap([], "Bachelor")
        assert gap is not None
        assert "no formal education" in gap.lower()

    def test_skill_suggestions(self):
        suggestions = SkillGapAnalyzer._skill_suggestions(["python", "java"], ["react"])
        assert len(suggestions) == 3
        assert any("python" in s for s in suggestions)

    def test_improvement_suggestions_strong(self):
        suggestions = SkillGapAnalyzer._improvement_suggestions(
            overall_score=90, matched_skills=["python", "react"],
            missing_required=[], missing_preferred=[],
            exp_gap=None, edu_gap=None, cert_gap=None,
        )
        assert len(suggestions) >= 1

    def test_improvement_suggestions_weak(self):
        suggestions = SkillGapAnalyzer._improvement_suggestions(
            overall_score=30, matched_skills=[],
            missing_required=["python", "java"], missing_preferred=["react"],
            exp_gap="Needs more experience", edu_gap="Below required", cert_gap=None,
        )
        assert len(suggestions) >= 3

    def test_interview_readiness_high(self):
        readiness = SkillGapAnalyzer._interview_readiness(overall_score=90, missing_required_count=0, exp_gap=None)
        assert readiness >= 90

    def test_interview_readiness_low(self):
        readiness = SkillGapAnalyzer._interview_readiness(overall_score=30, missing_required_count=3, exp_gap="gap")
        assert readiness < 40


# ─── Screening API Integration Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_screening_requires_auth(client):
    """Screening endpoints require authentication."""
    job_id = str(uuid.uuid4())
    response = await client.post(f"/api/v1/screening/jobs/{job_id}/screen")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_get_rankings_requires_auth(client):
    job_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/screening/jobs/{job_id}/rankings")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_get_candidate_screening_requires_auth(client):
    job_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/screening/jobs/{job_id}/candidates/{candidate_id}")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_my_scores_requires_auth(client):
    response = await client.get("/api/v1/screening/my-scores")
    assert response.status_code in (401, 403, 422)
