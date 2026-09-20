"""Phase 9 Skill2Job Learning Resource Intelligence tests.

Covers:
- Consolidated catalog integrity + verification metadata derivation
- Stable re-export of ``_RESOURCE_CATALOG`` from the Time-to-Ready module
- Catalog listing (filter / free-only / sorting)
- Deterministic skill mapping (exact / synonym / fallback)
- Optimization-mode ordering (fastest / cheapest actually change selection)
- Candidate-gated routes (recruiter → 403)
"""

import pytest
from httpx import AsyncClient

from app.skill2job.learning.agent import LearningResourceAgent
from app.skill2job.learning.resources import (
    RESOURCE_DATA_VERSION,
    _RESOURCE_CATALOG,
)
from app.skill2job.training.time_to_ready import TimeToReadyEngine


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Phase9 Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


# --- Catalog integrity & verification metadata ---


class TestCatalogMetadata:
    def test_catalog_has_expected_size(self):
        assert len(_RESOURCE_CATALOG) >= 22

    def test_catalog_still_importable_from_time_to_ready(self):
        from app.skill2job.training.time_to_ready import _RESOURCE_CATALOG as ttr_catalog

        assert ttr_catalog is _RESOURCE_CATALOG
        assert hasattr(TimeToReadyEngine, "_best_resource_for_skill")

    def test_resources_have_required_fields(self):
        required = [
            "resource_id", "title", "provider", "skills", "duration_hours",
            "is_free", "pricing_type", "difficulty", "format",
        ]
        for r in _RESOURCE_CATALOG:
            for field in required:
                assert field in r, f"Missing {field} in {r['resource_id']}"

    def test_verification_metadata_present_everywhere(self):
        for r in _RESOURCE_CATALOG:
            assert isinstance(r["verified"], bool), r["resource_id"]
            assert r["last_verified_at"] is None, r["resource_id"]
            assert r["description"], r["resource_id"]

    def test_verified_derived_from_audited_hosts(self):
        by_id = {r["resource_id"]: r for r in _RESOURCE_CATALOG}
        assert by_id["res_python_official"]["verified"] is True
        assert by_id["res_nptel_python"]["verified"] is True
        assert by_id["res_coursera_ml"]["verified"] is False
        assert by_id["res_numpy_docs"]["verified"] is False

    def test_version_constant_is_semantic(self):
        assert RESOURCE_DATA_VERSION.startswith("skill2job-resource-data")

    def test_free_resources_have_zero_cost(self):
        for r in _RESOURCE_CATALOG:
            if r["is_free"]:
                assert r.get("cost", 0) == 0, r["resource_id"]


# --- Agent: catalog listing ---


class TestListResources:
    def test_list_returns_all(self):
        result = LearningResourceAgent().list_resources(limit=100)
        assert result.total == len(_RESOURCE_CATALOG)
        assert result.version == RESOURCE_DATA_VERSION
        assert len(result.resources) == result.total
        for item in result.resources[:3]:
            assert isinstance(item.verified, bool)

    def test_list_free_only(self):
        result = LearningResourceAgent().list_resources(free_only=True, limit=100)
        assert result.resources
        assert all(r.is_free for r in result.resources)

    def test_list_skill_filter(self):
        result = LearningResourceAgent().list_resources(skill_filter="Python", limit=100)
        assert result.total >= 1
        for r in result.resources:
            haystack = f"{r.title} {r.provider} {' '.join(r.skills)}".lower()
            assert "python" in haystack

    def test_list_is_deterministic(self):
        a = LearningResourceAgent().list_resources(limit=100)
        b = LearningResourceAgent().list_resources(limit=100)
        assert [r.resource_id for r in a.resources] == [r.resource_id for r in b.resources]


# --- Agent: deterministic skill mapping ---


class TestSkillMapping:
    def test_exact_python_maps_exactly(self):
        result = LearningResourceAgent().resources_for_skill("Python")
        assert result.mapped is True
        assert result.resources
        assert result.resources[0].mapping_kind == "exact"
        # matches the stable engine rule: free → coverage → duration
        assert result.resources[0].resource.resource_id == "res_fastapi_tutorial"

    def test_exact_is_case_insensitive(self):
        result = LearningResourceAgent().resources_for_skill("python")
        assert result.mapped is True
        assert all(c.mapping_kind == "exact" for c in result.resources)

    def test_synonym_via_token_overlap(self):
        result = LearningResourceAgent().resources_for_skill("Machine Learning Engineer")
        assert result.mapped is True
        kinds = {c.mapping_kind for c in result.resources}
        assert "synonym" in kinds

    def test_unknown_skill_falls_back(self):
        result = LearningResourceAgent().resources_for_skill("Qubit Dance Cardio")
        assert result.mapped is False
        assert result.resources
        assert all(c.mapping_kind == "fallback" for c in result.resources)
        fallback_ids = {c.resource.resource_id for c in result.resources}
        assert fallback_ids <= {"res_skill_india", "res_skill_india_hub"}

    def test_empty_skill(self):
        result = LearningResourceAgent().resources_for_skill("   ")
        assert result.mapped is False
        assert result.resources == []

    def test_free_only_excludes_paid(self):
        result = LearningResourceAgent().resources_for_skill("Machine Learning", free_only=True)
        assert result.resources
        assert all(c.resource.is_free for c in result.resources)


# --- Agent: optimization mode actually changes selection ---


class TestOptimizationModes:
    def test_balanced_prefers_verified_coverage(self):
        result = LearningResourceAgent().resources_for_skill("Machine Learning", mode="balanced")
        assert result.resources[0].resource.resource_id == "res_pytorch_tutorials"

    def test_fastest_picks_shortest_resource(self):
        result = LearningResourceAgent().resources_for_skill("Machine Learning", mode="fastest")
        assert result.resources[0].resource.resource_id == "res_sklearn_docs"

    def test_cheapest_picks_free_before_paid(self):
        result = LearningResourceAgent().resources_for_skill("Machine Learning", mode="cheapest")
        assert result.resources[0].resource.is_free is True

    def test_modes_differ_deterministically(self):
        by_id = lambda mode: [c.resource.resource_id for c in
                              LearningResourceAgent().resources_for_skill("Machine Learning", mode=mode).resources]
        fastest = by_id("fastest")
        balanced = by_id("balanced")
        assert fastest[0] != balanced[0]


# --- Routes ---


@pytest.mark.asyncio
async def test_resources_endpoint_candidate(client: AsyncClient):
    tokens = await _register_and_login(client, "lr_list@test.com")
    headers = _headers(tokens)

    resp = await client.get("/api/v1/skill2job/learning/resources", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 22
    assert body["resources"]
    assert "verified" in body["resources"][0]
    assert body["version"].startswith("skill2job-resource-data")


@pytest.mark.asyncio
async def test_resource_mapping_endpoint_candidate(client: AsyncClient):
    tokens = await _register_and_login(client, "lr_map@test.com")
    headers = _headers(tokens)

    resp = await client.get("/api/v1/skill2job/learning/resources/Python", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mapped"] is True
    assert body["resources"][0]["mapping_kind"] == "exact"
    assert body["resources"][0]["resource"]["resource_id"] == "res_fastapi_tutorial"


@pytest.mark.asyncio
async def test_learning_endpoints_require_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Phase9", "rec_lr@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    headers = _headers(login.json())
    assert (
        await client.get("/api/v1/skill2job/learning/resources", headers=headers)
    ).status_code == 403
    assert (
        await client.get("/api/v1/skill2job/learning/resources/Python", headers=headers)
    ).status_code == 403