from dataclasses import dataclass, field


@dataclass
class Skill2JobState:
    """Conceptual state shared by future Skill2Job agents.

    Phase 1 defines the contract ONLY. LangGraph orchestration that consumes
    this state is a Phase 8 deliverable and is not implemented yet.
    """

    candidate_id: str | None = None
    input_type: str | None = None  # voice | resume | image | document | free_text
    raw_input: str | None = None
    profile: dict | None = None
    location: str | None = None
    target_roles: list[str] = field(default_factory=list)
    jobs: list[dict] = field(default_factory=list)
    matches: list[dict] = field(default_factory=list)
    skill_gaps: list[dict] = field(default_factory=list)
    opportunity_analysis: dict | None = None
    training_recommendations: list[dict] = field(default_factory=list)
    action_plan: dict | None = None
    errors: list[str] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)