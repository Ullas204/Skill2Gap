"""Phase 12 – Answer grading for all assessment question types."""

from __future__ import annotations

import re


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def grade_objective(question: dict, answer: dict) -> dict:
    """Auto-grade objective types (MCQ family + code output)."""
    qtype = question["question_type"]
    correct = question.get("correct_answer") or {}

    if qtype in {"mcq", "aptitude_quantitative", "aptitude_logical", "aptitude_verbal",
                 "technical_theory", "sql_mcq"}:
        selected = answer.get("option_index")
        expected = correct.get("option_index")
        is_correct = isinstance(selected, int) and selected == expected
        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0,
            "feedback": "Correct!" if is_correct else "Incorrect.",
        }

    if qtype == "sql_debug":
        # SQL debugging is presented as MCQ options.
        selected = answer.get("option_index")
        expected = correct.get("option_index")
        is_correct = isinstance(selected, int) and selected == expected
        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else 0.0,
            "feedback": "Correct!" if is_correct else "Incorrect.",
        }

    if qtype == "code_output":
        given = _normalize_text(str(answer.get("text", "")))
        expected = _normalize_text(str(correct.get("output", "")))
        is_correct = bool(given) and given == expected
        partial = 0.5 if not is_correct and expected and (
            expected[: max(len(expected) // 2, 4)] in given
        ) else 0.0
        return {
            "is_correct": is_correct,
            "score": 1.0 if is_correct else partial,
            "feedback": "Exact match." if is_correct else "Output does not match; check the concept being tested.",
        }

    raise ValueError(f"Unsupported objective type: {qtype}")


def grade_subjective(question: dict, answer_text: str) -> dict:
    """Rubric-keyword grading for subjective answers.

    Scores reflect ANSWER-QUALITY EVIDENCE (rubric coverage, structure,
    specificity) — never psychological traits or personality claims.
    """
    rubric: list[str] = (question.get("correct_answer") or {}).get("rubric", [])
    text = _normalize_text(answer_text)
    if not text:
        return {"is_correct": False, "score": 0.0, "dimensions": {}, "feedback": "No answer provided."}

    hits = [kw for kw in rubric if kw.lower() in text]
    coverage = len(hits) / len(rubric) if rubric else min(len(text.split()) / 120, 1.0)

    words = len(text.split())
    depth = min(words / 150, 1.0)
    structured = any(m in text for m in ("first", "second", "then ", "finally", "step")) or "\n" in answer_text
    communication = (0.6 if structured else 0.35) + 0.2 * depth
    communication = min(communication, 1.0)

    score = round(100 * (0.65 * coverage + 0.20 * depth + 0.15 * communication), 2)
    missing = [kw for kw in rubric if kw.lower() not in text]

    feedback_parts = [
        f"Covered {len(hits)}/{len(rubric)} key evaluation points."
        if rubric else "Answer received and evaluated on presentation evidence."
    ]
    if missing:
        feedback_parts.append(f"Consider addressing: {', '.join(missing[:4])}.")
    if not structured:
        feedback_parts.append("Structuring the answer into clear steps would strengthen it.")

    return {
        "is_correct": score >= 70,
        "score": score / 100,
        "dimensions": {
            "rubric_coverage": round(coverage * 100),
            "depth_evidence": round(depth * 100),
            "presentation_evidence": round(communication * 100),
        },
        "feedback": " ".join(feedback_parts),
    }


def grade_debugging(question: dict, answer_text: str) -> dict:
    """Debugging = identify bug keywords + provide corrected code."""
    keywords: list[str] = (question.get("correct_answer") or {}).get("keywords", [])
    text = _normalize_text(answer_text)
    if not text:
        return {"is_correct": False, "score": 0.0, "dimensions": {}, "feedback": "No answer provided."}
    hits = [k for k in keywords if k.lower() in text]
    ident = len(hits) / len(keywords) if keywords else 0
    has_code = any(m in answer_text for m in ("def ", "= ", "=>", "()", ";", "{")) and len(text.split()) > 12
    fix_score = 0.5 if has_code else 0.0
    explain = min(len(text.split()) / 80, 1.0) * 0.3
    score = min(ident * 0.55 + fix_score * 0.35 + explain, 1.0)
    parts = [f"Issue identification: {int(ident * 100)}% of key concepts mentioned."]
    parts.append("Corrected code detected." if has_code else "Provide concrete corrected code.")
    return {
        "is_correct": score >= 0.7,
        "score": round(score, 2),
        "dimensions": {
            "bug_identification": round(ident * 100),
            "fix_provided": round(fix_score * 100),
            "explanation_evidence": round(explain * 100),
        },
        "feedback": " ".join(parts),
    }


def grade_coding_from_run(run_result: dict, points: float = 1.0) -> dict:
    """Score a coding submission from sandbox execution results."""
    total = run_result.get("total_count", 0)
    passed = run_result.get("passed_count", 0)
    ratio = passed / total if total else 0.0
    timed_out = run_result.get("timed_out")
    runtime_err = not run_result.get("ok") and total == 0
    score = round(ratio, 2)
    parts = [f"Passed {passed}/{total} test cases."]
    if timed_out:
        parts.append("Solution exceeded the execution time limit.")
    elif runtime_err:
        parts.append(f"Runtime error: {(run_result.get('stderr') or '')[:200]}")
    elif passed < total:
        parts.append("Review failing cases — check edge cases (empty input, duplicates, boundaries).")
    else:
        parts.append("All test cases passed.")
    return {
        "is_correct": passed == total and total > 0,
        "score": score,
        "dimensions": {
            "test_cases_passed": f"{passed}/{total}",
            "execution_time_ms": run_result.get("execution_time_ms"),
            "complexity_estimate": run_result.get("complexity_estimate"),
        },
        "feedback": " ".join(parts),
    }
