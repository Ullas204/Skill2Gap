import enum


class RoleName(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "organization_admin"
    HR_MANAGER = "hr_manager"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"

    @classmethod
    def public_registration_roles(cls) -> set[str]:
        return {cls.CANDIDATE.value}

    @classmethod
    def organization_roles(cls) -> set[str]:
        return {cls.ORG_ADMIN.value, cls.HR_MANAGER.value, cls.RECRUITER.value}

    @classmethod
    def privileged_roles(cls) -> set[str]:
        return {cls.SUPER_ADMIN.value, cls.ORG_ADMIN.value, cls.HR_MANAGER.value, cls.RECRUITER.value}


# ─── Phase 12 – Assessment Platform ──────────────────────────────────


class AssessmentMode(str, enum.Enum):
    QUICK_TEST = "quick_test"
    TECHNICAL = "technical"
    APTITUDE = "aptitude"
    CODING = "coding"
    FULL_INTERVIEW = "full_technical_interview"
    CAMPUS = "campus_placement"
    EXPERIENCED = "experienced_developer"
    SYSTEM_DESIGN = "system_design"
    CUSTOM = "custom"


class AssessmentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AttemptStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ABANDONED = "abandoned"


class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    APTITUDE_QUANTITATIVE = "aptitude_quantitative"
    APTITUDE_LOGICAL = "aptitude_logical"
    APTITUDE_VERBAL = "aptitude_verbal"
    TECHNICAL_THEORY = "technical_theory"
    CODING = "coding"
    DEBUGGING = "debugging"
    CODE_OUTPUT = "code_output"
    SQL_MCQ = "sql_mcq"
    SQL_QUERY = "sql_query"
    SQL_DEBUG = "sql_debug"
    DATABASE_DESIGN = "database_design"
    SYSTEM_DESIGN = "system_design"
    SCENARIO = "scenario"
    CASE_STUDY = "case_study"
    RESUME_BASED = "resume_based"
    PROJECT_BASED = "project_based"
    BEHAVIORAL = "behavioral"
    SITUATIONAL_JUDGMENT = "situational_judgment"

    @classmethod
    def objective(cls) -> set[str]:
        """Auto-gradable against a stored correct answer."""
        return {
            cls.MCQ.value, cls.APTITUDE_QUANTITATIVE.value, cls.APTITUDE_LOGICAL.value,
            cls.APTITUDE_VERBAL.value, cls.TECHNICAL_THEORY.value, cls.CODE_OUTPUT.value,
            cls.SQL_MCQ.value, cls.SQL_DEBUG.value,
        }

    @classmethod
    def subjective(cls) -> set[str]:
        return {
            cls.SYSTEM_DESIGN.value, cls.SCENARIO.value, cls.CASE_STUDY.value,
            cls.RESUME_BASED.value, cls.PROJECT_BASED.value, cls.BEHAVIORAL.value,
            cls.SITUATIONAL_JUDGMENT.value, cls.DATABASE_DESIGN.value,
        }


class AssessmentDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class SkillCategory(str, enum.Enum):
    PROGRAMMING_LANGUAGES = "programming_languages"
    FRAMEWORKS = "frameworks"
    DATABASES = "databases"
    CLOUD = "cloud"
    DEVOPS = "devops"
    AI_ML = "ai_ml"
    TOOLS = "tools"
    SOFT_SKILLS = "soft_skills"


class Proficiency(str, enum.Enum):
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    NATIVE = "native"


class SkillProficiency(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class NotificationType(str, enum.Enum):
    WELCOME = "welcome"
    PROFILE_UPDATED = "profile_updated"
    RESUME_UPLOADED = "resume_uploaded"
    AVATAR_CHANGED = "avatar_changed"
    NEW_FEATURE = "new_feature"
    APPLICATION_STATUS = "application_status"
    RESUME_PARSED = "resume_parsed"
    GENERAL = "general"


class ResumeStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSED = "parsed"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SimulationStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def editable_states(cls) -> set[str]:
        """States that may still be edited through the Phase 1 CRUD API."""
        return {cls.DRAFT.value, cls.CANCELLED.value}


class SimulationEducationLevel(str, enum.Enum):
    """Education levels aligned with the platform's screening education scale."""
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"


class SimulationEducationRequirement(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    OPTIONAL = "optional"


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    REJECTED = "rejected"
    OFFERED = "offered"
    HIRED = "hired"
    WITHDRAWN = "withdrawn"


class StrengthLevel(str, enum.Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    LOW = "low"


class HiringRecommendation(str, enum.Enum):
    STRONGLY_RECOMMEND = "strongly_recommend"
    RECOMMEND = "recommend"
    CONSIDER = "consider"
    NOT_RECOMMENDED = "not_recommended"


class InterviewType(str, enum.Enum):
    MOCK = "mock"
    RECRUITER_SCHEDULED = "recruiter_scheduled"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class QuestionCategory(str, enum.Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    HR = "hr"
    SITUATIONAL = "situational"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"
    PROBLEM_SOLVING = "problem_solving"


class QuestionDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CodingProblemType(str, enum.Enum):
    CODING = "coding"
    MCQ = "mcq"
    SQL = "sql"
    DEBUGGING = "debugging"
    ALGORITHM = "algorithm"


class ReportType(str, enum.Enum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    HR = "hr"
    ADMIN = "admin"
    EXECUTIVE = "executive"


class ExportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


class AlertType(str, enum.Enum):
    HIRING_DELAY = "hiring_delay"
    LOW_VOLUME = "low_volume"
    BIAS_WARNING = "bias_warning"
    SECURITY_EVENT = "security_event"
    SYSTEM_HEALTH = "system_health"
    SCHEDULE_CONFLICT = "schedule_conflict"
    JOB_EXPIRING = "job_expiring"


class InsightCategory(str, enum.Enum):
    HIRING_DEMAND = "hiring_demand"
    CANDIDATE_SUCCESS = "candidate_success"
    SKILL_TREND = "skill_trend"
    BOTTLENECK = "bottleneck"
    PERFORMANCE = "performance"
    TREND = "trend"


# ── Phase 1: Identity + Organization + Authorization ───────────────


class AccountStatus(str, enum.Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class OrganizationStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class MembershipStatus(str, enum.Enum):
    INVITED = "invited"
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuditEventType(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    EMAIL_VERIFICATION = "email_verification"
    INVITATION_CREATED = "invitation_created"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_REVOKED = "invitation_revoked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    MEMBERSHIP_SUSPENDED = "membership_suspended"
    MEMBERSHIP_REVOKED = "membership_revoked"
    MEMBERSHIP_REACTIVATED = "membership_reactivated"
    ORGANIZATION_CREATED = "organization_created"
    ORGANIZATION_UPDATED = "organization_updated"
    ACCOUNT_SUSPENDED = "account_suspended"
    ACCOUNT_DEACTIVATED = "account_deactivated"
    ACCOUNT_REACTIVATED = "account_reactivated"
    AUTHORIZATION_FAILURE = "authorization_failure"
    TOKEN_REFRESH = "token_refresh"
    LOGOUT_ALL = "logout_all"
    SIMULATION_CREATED = "simulation_created"
    SIMULATION_UPDATED = "simulation_updated"
    SIMULATION_DELETED = "simulation_deleted"
    SIMULATION_VALIDATED = "simulation_validated"
    SIMULATION_STATUS_CHANGED = "simulation_status_changed"
    SIMULATION_RUN_STARTED = "simulation_run_started"
    SIMULATION_RUN_COMPLETED = "simulation_run_completed"
    SIMULATION_RUN_FAILED = "simulation_run_failed"
    SIMULATION_RUN_CANCELLED = "simulation_run_cancelled"
    RANKING_IMPACT_VIEWED = "ranking_impact_viewed"
    REQUIREMENT_IMPACT_VIEWED = "requirement_impact_viewed"
    REQUIREMENT_IMPACT_ANALYSIS_GENERATED = "requirement_impact_analysis_generated"


# ── Phase 4: Ranking Impact Analysis ──────────────────────────────


class CandidateMovementCategory(str, enum.Enum):
    """Deterministic classification of how a candidate moved between rankings.

    Thresholds are configurable and centralized in the ranking impact analyzer.
    The default configuration uses:
        SIGNIFICANTLY_IMPROVED: rank_change >= 10
        IMPROVED: rank_change >= 3
        UNCHANGED: -2 <= rank_change <= 2
        DECLINED: rank_change <= -3
        SIGNIFICANTLY_DECLINED: rank_change <= -10
    """

    SIGNIFICANTLY_IMPROVED = "significantly_improved"
    IMPROVED = "improved"
    UNCHANGED = "unchanged"
    DECLINED = "declined"
    SIGNIFICANTLY_DECLINED = "significantly_declined"


class ImpactSeverity(str, enum.Enum):
    """Neutral magnitude categories for ranking impact visualization.

    These describe the magnitude of movement, NOT whether the change is
    good or bad. HIGH_RANK_MOVEMENT means large movement occurred — it
    must NOT mean "bad strategy" or "good strategy".
    """

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ImpactType(str, enum.Enum):
    """Types of ranking impact analysis metrics.

    Each type represents a distinct analytical dimension of the
    simulation's effect on candidate rankings.
    """

    RANKING_DISTRIBUTION = "ranking_distribution"
    SCORE_DISTRIBUTION = "score_distribution"
    TOP_MOVERS = "top_movers"
    SHORTLIST_MOVEMENT = "shortlist_movement"
    QUALIFICATION_MOVEMENT = "qualification_movement"
    RANK_STABILITY = "rank_stability"
    THRESHOLD_IMPACT = "threshold_impact"


# ── Legacy role name aliases for backward compatibility ────────────


LEGACY_ROLE_MAP: dict[str, str] = {
    "admin": RoleName.ORG_ADMIN.value,
    "hr": RoleName.HR_MANAGER.value,
    "recruiter": RoleName.RECRUITER.value,
    "candidate": RoleName.CANDIDATE.value,
}
