from pydantic import BaseModel, Field

from app.domain.candidate_schemas import CandidateProfileResponse
from app.domain.intelligence_schemas import CandidateIntelligence


class InterestsUpdate(BaseModel):
    """Candidate interests (free-form labels; max 20)."""

    interests: list[str] = Field(default_factory=list, max_length=20)


class Skill2JobHealth(BaseModel):
    """Module availability status."""

    module: str
    status: str


class CapabilityItem(BaseModel):
    """A single Skill2Job capability and its implementation status."""

    key: str
    label: str
    status: str  # "available" | "deferred"
    phase: int


class Skill2JobCapabilities(BaseModel):
    """Phase-aware capability report for the Skill2Job module."""

    module: str
    profile_connected: bool
    capabilities: list[CapabilityItem]


class Skill2JobProfileResponse(BaseModel):
    """Existing candidate profile + derived intelligence (no duplication)."""

    connected: bool
    profile: CandidateProfileResponse
    intelligence: CandidateIntelligence | None = None


class PerceptionInputStatus(BaseModel):
    input_type: str
    configured: bool
    providers: list[str]


class PerceptionStatusResponse(BaseModel):
    """Perception provider availability (honest capability reporting)."""

    document: PerceptionInputStatus
    free_text: PerceptionInputStatus
    voice: PerceptionInputStatus
    image: PerceptionInputStatus


class PerceptionListResponse(BaseModel):
    items: list[dict]
    total: int