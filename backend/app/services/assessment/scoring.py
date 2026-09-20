"""Phase 12 – Automatic scoring: sections, skills, readiness, recommendation."""

from __future__ import annotations

SECTION_LABELS = {
    "mcq": "Technical MCQ",
    "aptitude_quantitative": "Quantitative Aptitude",
    "aptitude_logical": "Logical Reasoning",
    "aptitude_verbal": "Verbal Ability",
    "technical_theory": "CS Fundamentals",
    "coding": "Coding",
    "debugging": "Debugging",
    "code_output": "Code Output",
    "sql_mcq": "SQL Theory",
    "sql_query": "SQL Queries",
    "sql_debug": "SQL Debugging",
    "database_design": "Database Design",
    "system_design": "System Design",
    "scenario": "Scenario",
    "case_study": "Case Study",
    "resume_based": "Resume-Based",
    "project_based": "Project-Based",
    "behavioral": "Behavioral",
    "situational_judgment": "Situational Judgment",
}


def compute_result(
    questions: list[dict],
    answers: list[dict],
    *,
    negative_marking: float = 0.0,
    passing_score: int = 60,
) -> dict:
    """questions: [{id, question_type, skill, section, difficulty, points, estimated_time_seconds}]
    answers: [{question_id, score_fraction, is_correct, time_taken_seconds}]
    Returns the full result payload (section scores, skill scores, overall...).
    """
    q_by_id = {str(q["id"]): q for q in questions}
    sections: dict[str, dict] = {}
    skills: dict[str, list[float]] = {}
    difficulties: dict[str, dict] = {}
    total_earned = 0.0
    total_possible = 0.0
    correct_count = 0
    objective_count = 0
    time_taken_total = 0.0
    time_expected_total = 0.0

    for a in answers:
        q = q_by_id.get(str(a.get("question_id")))
        if not q:
            continue
        frac = float(a.get("score_fraction") or 0.0)
        points = float(q.get("points", 1.0))
        is_correct = a.get("is_correct")
        taken = a.get("time_taken_seconds")

        sec = q.get("section") or SECTION_LABELS.get(q["question_type"], q["question_type"])
        s = sections.setdefault(sec, {
            "section": sec,
            "question_type": q["question_type"],
            "earned": 0.0, "possible": 0.0, "correct": 0, "answered": 0,
        })
        earned = points * frac
        # Negative marking applies to wrong OBJECTIVE answers only.
        if is_correct is False and q["question_type"] in {
            "mcq", "aptitude_quantitative", "aptitude_logical", "aptitude_verbal",
            "technical_theory", "code_output", "sql_mcq", "sql_debug",
        }:
            earned -= negative_marking
            earned = max(earned, -points)  # floor at -points
        s["earned"] += earned
        s["possible"] += points
        s["answered"] += 1
        if is_correct:
            s["correct"] += 1

        skills.setdefault(q.get("skill", "General"), []).append(frac)
        d = q.get("difficulty", "medium")
        dd = difficulties.setdefault(d, {"earned": 0.0, "possible": 0.0})
        dd["earned"] += frac * 100
        dd["possible"] += 100

        total_earned += max(earned, 0.0) if negative_marking == 0 else earned
        total_possible += points
        time_taken_total += taken or 0
        time_expected_total += q.get("estimated_time_seconds", 90)

        if is_correct is not None:
            objective_count += 1
            if is_correct:
                correct_count += 1

    for sec_data in sections.values():
        sec_data["percentage"] = round(
            (sec_data["earned"] / sec_data["possible"]) * 100, 2
        ) if sec_data["possible"] else 0.0
        sec_data["accuracy"] = round(
            sec_data["correct"] / sec_data["answered"] * 100, 2
        ) if sec_data["answered"] else None

    skill_scores = {
        k: round(sum(v) / len(v) * 100, 2) for k, v in skills.items() if v
    }
    strong = sorted([k for k, v in skill_scores.items() if v >= 70])
    weak = sorted([k for k, v in skill_scores.items() if v < 50])

    overall = round((total_earned / total_possible) * 100, 2) if total_possible else 0.0
    overall = max(overall, 0.0)
    accuracy = round(correct_count / objective_count * 100, 2) if objective_count else 0.0
    efficiency = (time_expected_total / time_taken_total) if time_taken_total else 1.0
    time_management = round(min(efficiency, 1.5) / 1.5 * 100, 2)

    if overall >= 85:
        readiness, rec = "interview_ready", "strong_hire"
    elif overall >= 70:
        readiness, rec = "mostly_ready", "hire"
    elif overall >= passing_score:
        readiness, rec = "needs_preparation", "consider"
    else:
        readiness, rec = "not_ready", "reject"

    recommended = sorted({t for q in questions for t in _weak_topics(q, q_by_id, answers)}) or weak[:4]
    summary = (
        f"Overall {overall:.0f}/100 ({readiness.replace('_', ' ')}). "
        f"Strongest: {', '.join(strong[:3]) or 'n/a'}. "
        f"Focus areas: {', '.join(weak[:3]) or 'none flagged'}."
    )

    return {
        "section_scores": [
            {
                "section": s["section"],
                "question_type": s["question_type"],
                "earned": round(s["earned"], 2),
                "possible": round(s["possible"], 2),
                "percentage": s["percentage"],
                "accuracy": s["accuracy"],
            }
            for s in sections.values()
        ],
        "skill_scores": skill_scores,
        "difficulty_performance": {
            d: round(v["earned"] / v["possible"], 2) if v["possible"] else 0.0
            for d, v in difficulties.items()
        },
        "strong_skills": strong,
        "weak_skills": weak,
        "recommended_topics": recommended[:6],
        "overall_score": overall,
        "accuracy": accuracy,
        "time_management": time_management,
        "readiness_level": readiness,
        "recommendation": rec,
        "ai_summary": summary,
    }


def _weak_topics(question: dict, q_by_id: dict, answers: list[dict]) -> set[str]:
    a = next((a for a in answers if str(a.get("question_id")) == str(question["id"])), None)
    if a and a.get("score_fraction", 1.0) < 0.5:
        topic = question.get("topic") or ""
        if topic and topic != "general":
            return {topic.replace("_", " ").title()}
    return set()
