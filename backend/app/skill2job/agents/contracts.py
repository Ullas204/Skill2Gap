"""Future Skill2Job agent interface contracts.

Phase 1 defines only the typed input/output contracts for the agents that will
be implemented in later phases. No agent intelligence exists yet; these are
purely architectural seams so later orchestration can be wired without
refactoring the Skill2Job layer.
"""

from typing import Any, Protocol


class PerceptionAgent(Protocol):
    """Phase 2 — Understand unstructured input (voice, resume, image, document, free text)."""

    async def perceive(self, raw_input: str, input_type: str) -> dict[str, Any]:
        """Return {entities, skills_hint, intent, confidence, raw} for the given input."""
        ...


class ProfileAgent(Protocol):
    """Phase 3 — Reconcile perceived input into the existing candidate profile."""

    async def build_profile(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return an updated candidate profile payload owned by existing intelligence."""
        ...


class LocalJobAgent(Protocol):
    """Phase 4 — Fetch relevant local job opportunities from the Job system / curated catalog."""

    async def fetch_jobs(self, profile: dict[str, Any], location: str | None) -> list[dict[str, Any]]:
        ...


class MatchingAgent(Protocol):
    """Phase 5 — Match the candidate profile against jobs (reuses existing MatchingEngine)."""

    async def match(self, profile: dict[str, Any], jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...


class SkillGapAgent(Protocol):
    """Phase 6 — Determine specific missing skills (reuses existing SkillGraph + gap analysis)."""

    async def analyze(self, candidate_profile: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
        """Return {missing_required, missing_preferred, suggestions, readiness}."""
        ...


class OpportunityAgent(Protocol):
    """Phase 7 — Simulate which opportunities each new skill unlocks."""

    async def simulate(self, candidate_profile: dict[str, Any], skill: str) -> dict[str, Any]:
        ...


class TrainingAgent(Protocol):
    """Phase 8 — Recommend training/resources and produce a personalized action plan."""

    async def recommend(self, gaps: dict[str, Any], opportunities: dict[str, Any]) -> dict[str, Any]:
        ...