"""Phase 12 – AI question quality-control layer.

Every generated question passes validation before it can enter an
assessment: structural integrity, single-answer guarantee, option
validity, and duplicate detection.
"""

from __future__ import annotations

import hashlib
import re


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def question_fingerprint(question: dict) -> str:
    """Stable hash of the question text (for duplicate prevention)."""
    return hashlib.sha1(_norm(question.get("question_text", "")).encode()).hexdigest()


def validate_question(q: dict) -> tuple[bool, str]:
    qtype = q.get("question_type", "")
    text = (q.get("question_text") or "").strip()
    if len(text) < 10:
        return False, "question_text missing or too short"

    content = q.get("content") or {}

    # Objective MCQ-shaped types must carry >=3 unique options + valid answer index.
    mcq_shaped = {
        "mcq", "aptitude_quantitative", "aptitude_logical", "aptitude_verbal",
        "technical_theory", "sql_mcq", "sql_debug",
    }
    if qtype in mcq_shaped:
        options = content.get("options") or []
        if len(options) < 3:
            return False, "needs at least 3 options"
        normalized = [_norm(str(o)) for o in options]
        if len(set(normalized)) != len(normalized):
            return False, "duplicate options"
        idx = (q.get("correct_answer") or {}).get("option_index")
        if not isinstance(idx, int) or not (0 <= idx < len(options)):
            return False, "correct answer index out of range"
        if not (q.get("explanation") or "").strip():
            return False, "missing explanation"

    elif qtype == "code_output":
        ca = q.get("correct_answer") or {}
        if not str(ca.get("output", "")).strip():
            return False, "code_output missing expected output"
        if not (content.get("snippet") or "").strip():
            return False, "code_output missing snippet"

    elif qtype == "coding":
        tests = content.get("test_cases") or []
        if not tests:
            return False, "coding question has no test cases"
        for tc in tests:
            if "args" not in tc or "expected" not in tc:
                return False, "malformed test case"
        if not (content.get("starter_code") or "").strip():
            return False, "coding question missing starter code"

    elif qtype == "sql_query":
        if not (content.get("reference_query") or "").strip():
            return False, "sql_query missing reference query"

    elif qtype == "debugging":
        if not (content.get("buggy_code") or "").strip():
            return False, "debugging question missing buggy code"
        if not ((q.get("correct_answer") or {}).get("keywords")):
            return False, "debugging question missing grading keywords"

    elif qtype in {"system_design", "scenario", "case_study", "resume_based",
                   "project_based", "behavioral", "situational_judgment",
                   "database_design"}:
        rubric = (q.get("correct_answer") or {}).get("rubric")
        if not rubric and not (q.get("correct_answer") or {}).get("keywords"):
            return False, "subjective question missing evaluation rubric"

    else:
        return False, f"unknown question_type '{qtype}'"

    return True, ""


def sanitize_batch(questions: list[dict]) -> list[dict]:
    """Validate a batch, drop duplicates/invalids. Returns clean questions."""
    seen: set[str] = set()
    clean: list[dict] = []
    for q in questions:
        ok, _reason = validate_question(q)
        if not ok:
            continue
        fp = question_fingerprint(q)
        if fp in seen:
            continue
        seen.add(fp)
        clean.append(q)
    return clean
