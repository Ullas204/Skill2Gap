"""Adapters that reuse existing platform intelligence without duplicating logic."""

from app.skill2job.adapters.candidate_adapter import CandidateAdapter
from app.skill2job.adapters.skill_graph_adapter import SkillGraphAdapter

__all__ = ["CandidateAdapter", "SkillGraphAdapter"]