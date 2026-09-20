"""Phase 8 - AI Interview Intelligence Platform

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── interviews ───────────────────────────────────────────────
    op.create_table(
        "interviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("recruiter_id", sa.Uuid(), nullable=True),
        sa.Column("interview_type", sa.String(30), nullable=False, server_default="mock"),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("questions_answered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interviews_job_id", "interviews", ["job_id"])
    op.create_index("ix_interviews_candidate_id", "interviews", ["candidate_id"])
    op.create_index("ix_interviews_recruiter_id", "interviews", ["recruiter_id"])

    # ─── interview_questions ──────────────────────────────────────
    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interview_questions_interview_id", "interview_questions", ["interview_id"])

    # ─── interview_answers ────────────────────────────────────────
    op.create_table(
        "interview_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("time_taken_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", name="uq_answer_question"),
    )

    # ─── interview_evaluations ────────────────────────────────────
    op.create_table(
        "interview_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("answer_id", sa.Uuid(), nullable=False),
        sa.Column("technical_accuracy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completeness", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("communication", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("problem_solving", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("improvement_suggestions", sa.JSON(), nullable=True),
        sa.Column("follow_up_questions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["answer_id"], ["interview_answers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("answer_id", name="uq_evaluation_answer"),
    )

    # ─── interview_scorecards ─────────────────────────────────────
    op.create_table(
        "interview_scorecards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("technical_skills", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("communication", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("teamwork", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leadership", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("problem_solving", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("culture_fit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("learning_ability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation", sa.String(30), nullable=False, server_default="consider"),
        sa.Column("hiring_confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recruiter_notes", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", name="uq_scorecard_interview"),
    )

    # ─── coding_assessments ───────────────────────────────────────
    op.create_table(
        "coding_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("problem_title", sa.String(255), nullable=False),
        sa.Column("problem_description", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("test_cases", sa.JSON(), nullable=True),
        sa.Column("expected_output", sa.JSON(), nullable=True),
        sa.Column("candidate_solution", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_assessments_interview_id", "coding_assessments", ["interview_id"])


def downgrade() -> None:
    op.drop_index("ix_coding_assessments_interview_id", table_name="coding_assessments")
    op.drop_table("coding_assessments")
    op.drop_table("interview_scorecards")
    op.drop_table("interview_evaluations")
    op.drop_table("interview_answers")
    op.drop_index("ix_interview_questions_interview_id", table_name="interview_questions")
    op.drop_table("interview_questions")
    op.drop_index("ix_interviews_recruiter_id", table_name="interviews")
    op.drop_index("ix_interviews_candidate_id", table_name="interviews")
    op.drop_index("ix_interviews_job_id", table_name="interviews")
    op.drop_table("interviews")
