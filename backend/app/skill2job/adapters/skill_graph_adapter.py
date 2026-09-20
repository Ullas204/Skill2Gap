from app.services.screening.skill_graph import SkillGraph


class SkillGraphAdapter:
    """Read-only adapter over the existing in-memory skill knowledge graph.

    Reuses the platform's SkillGraph rather than duplicating skill ontology or
    similarity logic. Future phases (skill gap reasoning, transferable skill
    discovery) resolve through this adapter.
    """

    @staticmethod
    def normalize(skill: str) -> str:
        return SkillGraph.normalize(skill)

    @staticmethod
    def find_canonical(skill: str) -> str | None:
        return SkillGraph.find_canonical(skill)

    @staticmethod
    def are_synonyms(skill_a: str, skill_b: str) -> bool:
        return SkillGraph.are_synonyms(skill_a, skill_b)

    @staticmethod
    def similarity(skill_a: str, skill_b: str) -> float:
        return SkillGraph.similarity_score(skill_a, skill_b)

    @staticmethod
    def related_skills(skill: str) -> list[str]:
        return SkillGraph.get_related_skills(skill)