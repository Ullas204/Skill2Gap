import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import (
    AccountStatus,
    ApplicationStatus,
    AssessmentDifficulty,
    AssessmentMode,
    AssessmentStatus,
    AttemptStatus,
    CodingProblemType,
    EmploymentType,
    Gender,
    HiringRecommendation,
    InterviewStatus,
    InterviewType,
    InvitationStatus,
    JobStatus,
    MembershipStatus,
    NotificationType,
    OrganizationStatus,
    Proficiency,
    QuestionCategory,
    QuestionDifficulty,
    QuestionType,
    ResumeStatus,
    SkillCategory,
    SkillProficiency,
    StrengthLevel,
)


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    account_status: Mapped[str] = mapped_column(
        String(30), default=AccountStatus.ACTIVE.value, nullable=False, index=True,
    )

    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan",
    )
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="[OrganizationMembership.user_id]",
    )
    invitations_sent: Mapped[list["Invitation"]] = relationship(
        "Invitation", foreign_keys="Invitation.invited_by_id", back_populates="invited_by",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    users: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan",
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="roles")
    role: Mapped["Role"] = relationship("Role", back_populates="users")


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# ═══════════════════════════════════════════════════════════════════
# Phase 1 – Organization + Multi-Tenant Architecture
# ═══════════════════════════════════════════════════════════════════


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default=OrganizationStatus.ACTIVE.value, nullable=False, index=True,
    )

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership", back_populates="organization", cascade="all, delete-orphan",
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation", back_populates="organization", cascade="all, delete-orphan",
    )
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="organization")


class OrganizationMembership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default=MembershipStatus.ACTIVE.value, nullable=False,
    )
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    invited_by: Mapped["User | None"] = relationship("User", foreign_keys=[invited_by_id])


class Invitation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invitations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    invited_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default=InvitationStatus.PENDING.value, nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="invitations")
    invited_by: Mapped["User"] = relationship("User", foreign_keys=[invited_by_id], back_populates="invitations_sent")
    accepted_by: Mapped["User | None"] = relationship("User", foreign_keys=[accepted_by_id])

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_token(token: str) -> str:
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()


class CandidateProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True,
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interests: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", backref="candidate_profile", lazy="joined")

    education: Mapped[list["Education"]] = relationship("Education", back_populates="profile")
    experiences: Mapped[list["Experience"]] = relationship("Experience", back_populates="profile")
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship("CandidateSkill", back_populates="profile")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="profile")
    certifications: Mapped[list["Certification"]] = relationship("Certification", back_populates="profile")
    languages: Mapped[list["Language"]] = relationship("Language", back_populates="profile")


class Education(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "education"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cgpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="education")


class Experience(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "experiences"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    employment_type: Mapped[EmploymentType | None] = mapped_column(String(50), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="experiences")


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[SkillCategory] = mapped_column(String(50), nullable=False)


class CandidateSkill(Base, TimestampMixin):
    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), primary_key=True,
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True,
    )
    proficiency: Mapped[SkillProficiency] = mapped_column(String(20), default=SkillProficiency.INTERMEDIATE, nullable=False)
    years_of_experience: Mapped[float | None] = mapped_column(Float, nullable=True)

    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="candidate_skills")
    skill: Mapped["Skill"] = relationship("Skill", lazy="joined")


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    live_demo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="projects")


class Certification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "certifications"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="certifications")


class Language(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "languages"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    language: Mapped[str] = mapped_column(String(100), nullable=False)
    reading: Mapped[Proficiency] = mapped_column(String(20), default=Proficiency.INTERMEDIATE, nullable=False)
    writing: Mapped[Proficiency] = mapped_column(String(20), default=Proficiency.INTERMEDIATE, nullable=False)
    speaking: Mapped[Proficiency] = mapped_column(String(20), default=Proficiency.INTERMEDIATE, nullable=False)

    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="languages")


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(String(50), default=NotificationType.GENERAL, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", backref="notifications")


class Resume(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ResumeStatus] = mapped_column(String(20), default=ResumeStatus.UPLOADED, nullable=False)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    user: Mapped["User"] = relationship("User", backref="resumes")
    profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", backref="resumes")


class ParsedResumeData(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "parsed_resume_data"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    personal_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    education: Mapped[list | None] = mapped_column(JSON, nullable=True)
    experience: Mapped[list | None] = mapped_column(JSON, nullable=True)
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    projects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    certifications: Mapped[list | None] = mapped_column(JSON, nullable=True)
    languages: Mapped[list | None] = mapped_column(JSON, nullable=True)

    resume: Mapped["Resume"] = relationship(
        "Resume",
        backref=backref(
            "parsed_data",
            uselist=False,
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
        uselist=False,
    )


class ResumeAnalysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resume_analysis"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    quality_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    readability_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    professionalism_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    keyword_optimization_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ats_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_sections: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    section_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    keyword_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    formatting_issues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    skill_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    industry_keywords: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[list | None] = mapped_column(JSON, nullable=True)

    resume: Mapped["Resume"] = relationship(
        "Resume",
        backref=backref(
            "analysis",
            uselist=False,
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
        uselist=False,
    )


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(String(50), nullable=False)
    experience_required: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_required: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    preferred_skills: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_deadline: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[JobStatus] = mapped_column(String(20), default=JobStatus.DRAFT, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    recruiter: Mapped["User"] = relationship("User", backref="jobs")
    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="jobs")
    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication", back_populates="job", cascade="all, delete-orphan",
    )


class JobApplication(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True,
    )
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(String(20), default=ApplicationStatus.APPLIED, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    candidate: Mapped["User"] = relationship("User", backref="job_applications")
    resume: Mapped["Resume | None"] = relationship("Resume", backref="job_applications")
    recruiter_notes: Mapped[list["RecruiterNote"]] = relationship(
        "RecruiterNote", back_populates="application", cascade="all, delete-orphan",
    )


class SavedJob(Base, TimestampMixin):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_candidate_saved_job"),)

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True,
    )

    job: Mapped["Job"] = relationship("Job", backref="saved_by")


class RecruiterNote(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recruiter_notes"

    job_application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)

    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="recruiter_notes")
    recruiter: Mapped["User"] = relationship("User", backref="recruiter_notes")


class ScreeningResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "screening_results"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_screening_job_candidate"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True,
    )
    overall_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skill_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    experience_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    education_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    project_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    certification_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    location_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    employment_type_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    semantic_match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing_required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing_preferred_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[HiringRecommendation] = mapped_column(
        String(30), default=HiringRecommendation.CONSIDER, nullable=False,
    )
    strength_level: Mapped[StrengthLevel] = mapped_column(
        String(20), default=StrengthLevel.AVERAGE, nullable=False,
    )

    job: Mapped["Job"] = relationship("Job", backref="screening_results")
    candidate: Mapped["User"] = relationship("User", backref="screening_results")
    resume: Mapped["Resume | None"] = relationship("Resume", backref="screening_results")


class CandidateRanking(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_rankings"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_ranking_job_candidate"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    screening_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("screening_results.id", ondelete="CASCADE"), nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_change: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    strength_level: Mapped[StrengthLevel] = mapped_column(
        String(20), default=StrengthLevel.AVERAGE, nullable=False,
    )

    job: Mapped["Job"] = relationship("Job", backref="candidate_rankings")
    candidate: Mapped["User"] = relationship("User", backref="candidate_rankings")
    screening_result: Mapped["ScreeningResult"] = relationship("ScreeningResult", backref="ranking")


class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User | None"] = relationship("User", backref="audit_logs")
    organization: Mapped["Organization | None"] = relationship("Organization")


class SkillGapAnalysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "skill_gap_analyses"
    __table_args__ = (UniqueConstraint("screening_result_id", name="uq_skill_gap_screening"),)

    screening_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("screening_results.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    missing_required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing_preferred_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    experience_gap_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_gap_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    certification_gap_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    improvement_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    interview_readiness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    screening_result: Mapped["ScreeningResult"] = relationship("ScreeningResult", backref="skill_gap_analysis")


# ═══════════════════════════════════════════════════════════════════
# Phase 8 – Interview Intelligence
# ═══════════════════════════════════════════════════════════════════


class Interview(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interviews"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    interview_type: Mapped[InterviewType] = mapped_column(
        String(30), default=InterviewType.MOCK, nullable=False,
    )
    status: Mapped[InterviewStatus] = mapped_column(
        String(20), default=InterviewStatus.SCHEDULED, nullable=False,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    job: Mapped["Job"] = relationship("Job", backref="interviews")
    candidate: Mapped["User"] = relationship("User", foreign_keys=[candidate_id], backref="candidate_interviews")
    recruiter: Mapped["User | None"] = relationship("User", foreign_keys=[recruiter_id], backref="recruiter_interviews")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="interview", cascade="all, delete-orphan",
    )
    scorecard: Mapped["InterviewScorecard | None"] = relationship(
        "InterviewScorecard", back_populates="interview", uselist=False,
    )


class InterviewQuestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_questions"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[QuestionCategory] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(String(20), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    interview: Mapped["Interview"] = relationship("Interview", back_populates="questions")
    answer: Mapped["InterviewAnswer | None"] = relationship(
        "InterviewAnswer", back_populates="question", uselist=False,
    )


class InterviewAnswer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    question: Mapped["InterviewQuestion"] = relationship("InterviewQuestion", back_populates="answer")
    evaluation: Mapped["InterviewEvaluation | None"] = relationship(
        "InterviewEvaluation", back_populates="answer", uselist=False,
    )


class InterviewEvaluation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_evaluations"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_answers.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    technical_accuracy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completeness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    communication: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    problem_solving: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relevance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_suggestions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    follow_up_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    answer: Mapped["InterviewAnswer"] = relationship("InterviewAnswer", back_populates="evaluation")


class InterviewScorecard(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_scorecards"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    technical_skills: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    communication: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    teamwork: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leadership: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    problem_solving: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    culture_fit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    learning_ability: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommendation: Mapped[HiringRecommendation] = mapped_column(
        String(30), default=HiringRecommendation.CONSIDER, nullable=False,
    )
    hiring_confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recruiter_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    interview: Mapped["Interview"] = relationship("Interview", back_populates="scorecard")


class CodingAssessment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coding_assessments"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    problem_title: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(String(20), nullable=False)
    category: Mapped[CodingProblemType] = mapped_column(String(30), nullable=False)
    test_cases: Mapped[list | None] = mapped_column(JSON, nullable=True)
    expected_output: Mapped[list | None] = mapped_column(JSON, nullable=True)
    candidate_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    interview: Mapped["Interview"] = relationship("Interview", backref="coding_assessments")


# ═══════════════════════════════════════════════════════════════════
# Phase 12 – Assessment Platform (extends Interview Intelligence)
# ═══════════════════════════════════════════════════════════════════


class Assessment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessments"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    mode: Mapped[AssessmentMode] = mapped_column(
        String(40), default=AssessmentMode.CUSTOM, nullable=False,
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        String(20), default=AssessmentStatus.PUBLISHED, nullable=False, index=True,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    passing_score: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    negative_marking: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    allowed_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    adaptive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    job: Mapped["Job | None"] = relationship("Job")
    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan",
    )
    attempts: Mapped[list["CandidateAssessment"]] = relationship(
        "CandidateAssessment", back_populates="assessment", cascade="all, delete-orphan",
    )


class AssessmentQuestion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_questions"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_type: Mapped[QuestionType] = mapped_column(String(40), nullable=False, index=True)
    skill: Mapped[str] = mapped_column(String(80), default="general", nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(120), default="general", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_time_seconds: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    section: Mapped[str] = mapped_column(String(80), default="general", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="questions")
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase", back_populates="question", cascade="all, delete-orphan",
    )


class TestCase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_test_cases"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question: Mapped["AssessmentQuestion"] = relationship("AssessmentQuestion", back_populates="test_cases")


class CandidateAssessment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_assessments"
    __table_args__ = (
        UniqueConstraint("assessment_id", "candidate_id", "attempt_number"),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        String(20), default=AttemptStatus.ASSIGNED, nullable=False, index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    question_order: Mapped[list | None] = mapped_column(JSON, nullable=True)
    integrity_events: Mapped[list | None] = mapped_column(JSON, nullable=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="attempts")
    answers: Mapped[list["CandidateAnswer"]] = relationship(
        "CandidateAnswer", back_populates="attempt", cascade="all, delete-orphan",
    )
    result: Mapped["AssessmentResult | None"] = relationship(
        "AssessmentResult", back_populates="attempt", uselist=False,
    )


class CandidateAnswer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_assessment_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_assessments.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    answer_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score_awarded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    attempt: Mapped["CandidateAssessment"] = relationship("CandidateAssessment", back_populates="answers")
    question: Mapped["AssessmentQuestion"] = relationship("AssessmentQuestion")
    coding_submission: Mapped["CodingSubmission | None"] = relationship(
        "CodingSubmission", back_populates="answer", uselist=False,
    )


class CodingSubmission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_coding_submissions"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_assessment_answers.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    language: Mapped[str] = mapped_column(String(30), default="python", nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    test_results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    complexity_estimate: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    answer: Mapped["CandidateAnswer"] = relationship("CandidateAnswer", back_populates="coding_submission")


class AssessmentResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessment_results"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_assessments.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    section_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_management: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    strong_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    weak_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommended_topics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    readiness_level: Mapped[str] = mapped_column(String(30), default="not_ready", nullable=False)
    recommendation: Mapped[str] = mapped_column(String(30), default="consider", nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempt: Mapped["CandidateAssessment"] = relationship("CandidateAssessment", back_populates="result")


# ═══════════════════════════════════════════════════════════════════
# Phase 13 – Evidence-Grounded Job Matching Intelligence
# ═══════════════════════════════════════════════════════════════════


class JobRequirementExtraction(Base, UUIDMixin, TimestampMixin):
    """Cached structured requirement extraction for a job description.

    One row per job: re-extraction only happens when the job version or the
    extractor version changes, so repeated page loads never re-parse the JD.
    """

    __tablename__ = "job_requirement_extractions"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True,
    )
    job_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(20), nullable=False)
    requirements: Mapped[dict] = mapped_column(JSON, nullable=False)

    job: Mapped["Job"] = relationship("Job", backref="requirement_extraction")


class JobFitAnalysis(Base, UUIDMixin, TimestampMixin):
    """Persisted evidence-grounded fit analysis for a candidate against a job.

    The full requirement-level result (status, evidence strength, evidence
    quotes, alignment, gaps, summary) is stored as JSON so it can be replayed
    without recomputation while remaining auditable.
    """

    __tablename__ = "job_fit_analyses"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_fit_job_candidate"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True,
    )
    overall_fit: Mapped[str] = mapped_column(String(30), nullable=False)
    fit_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)
    job_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)

    job: Mapped["Job"] = relationship("Job", backref="fit_analyses")
    candidate: Mapped["User"] = relationship("User", backref="fit_analyses")
    resume: Mapped["Resume | None"] = relationship("Resume", backref="fit_analyses")


class CandidateEvidenceIntel(Base, UUIDMixin, TimestampMixin):
    """Cached profile-level evidence intelligence for one candidate (Phase 3).

    One row per candidate. The full result (strengths, skill depth, review
    flags, questions, summary) is stored as JSON so page loads replay it
    without recomputation or extra LLM calls. Regenerated when the resume
    changes or the engine version is bumped.
    """

    __tablename__ = "candidate_evidence_intels"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True,
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True,
    )
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)

    candidate: Mapped["User"] = relationship("User", backref="evidence_intel")
    resume: Mapped["Resume | None"] = relationship("Resume", backref="evidence_intel")
