"""Phase 12 – Assessment question generation from curated banks.

Builds per-section question sets from the deterministic banks in
``question_banks`` (offline-safe), validates every item through the
quality-control layer and de-duplicates the final paper.
"""

from __future__ import annotations

import random
import re

from app.services.assessment import question_banks as qb
from app.services.assessment.validator import sanitize_batch

_MCQ_SHAPED = {"mcq", "technical_theory", "sql_mcq"}


def _difficulties(difficulty: str) -> list[str]:
    if difficulty == "mixed":
        return ["easy", "medium", "hard"]
    return [difficulty]


def _sample(pool: list[dict], count: int, rng: random.Random) -> list[dict]:
    pool = list(pool)
    rng.shuffle(pool)
    return pool[:count]


def _skill_pool(skill: str) -> list[dict]:
    key = (skill or "").lower()
    if key in qb.TECHNICAL_MCQ:
        return qb.TECHNICAL_MCQ[key]
    aliases = {"js": "javascript", "ts": "javascript", "postgres": "sql",
               "postgresql": "sql", "mysql": "sql", "node": "javascript",
               "nodejs": "javascript", "py": "python", "k8s": "docker"}
    alias = aliases.get(key)
    if alias:
        return qb.TECHNICAL_MCQ.get(alias, [])
    # partial match
    for k, v in qb.TECHNICAL_MCQ.items():
        if k in key or key in k:
            return v
    return []


def _build_objective(section: dict, rng: random.Random) -> list[dict]:
    qtype = section["question_type"]
    count = section["count"]
    skills = section.get("skills") or []
    diffs = _difficulties(section.get("difficulty", "medium"))
    out: list[dict] = []

    if qtype in {"mcq", "technical_theory"}:
        pools: list[dict] = []
        for s in skills or list(qb.TECHNICAL_MCQ.keys()):
            for q in _skill_pool(s):
                if not diffs or q["difficulty"] in diffs:
                    pools.append({**q, "question_type": qtype})
        if len(pools) < count:
            theory = [dict(t, question_type=qtype) for t in qb.TECH_THEORY_MCQ
                      if not diffs or t["difficulty"] in diffs]
            pools.extend(theory)
        out.extend(_sample(pools, count, rng))

    elif qtype == "sql_mcq":
        pool = [dict(q, question_type="sql_mcq") for q in qb.SQL_MCQ_BANK
                if not diffs or q["difficulty"] in diffs]
        out.extend(_sample(pool, count, rng))

    elif qtype == "aptitude_quantitative":
        topics = list(qb.QUANT_GENERATORS)
        seen_texts: set[str] = set()
        attempts = 0
        while len(out) < count and attempts < count * 6:
            attempts += 1
            topic = topics[len(out) % len(topics)]
            if section.get("skills"):
                wanted = section["skills"][len(out) % len(section["skills"])].lower().replace(" ", "_")
                if wanted in qb.QUANT_GENERATORS:
                    topic = wanted
            gen_q = qb.QUANT_GENERATORS[topic](rng)
            fp = re.sub(r"\W+", "", gen_q["question_text"].lower())[:80]
            if fp in seen_texts:
                continue
            seen_texts.add(fp)
            gen_q["topic"] = gen_q.get("topic", topic)
            gen_q["question_type"] = qtype
            out.append(gen_q)

    elif qtype == "aptitude_logical":
        pool: list[dict] = []
        for d in diffs:
            pool.append(qb.gen_number_series(rng))
        pool.extend([dict(q, question_type=qtype) for q in qb.LOGICAL_CURATED])
        seen_fp = set()
        uniq = []
        for q in pool:
            fp = re.sub(r"\W+", "", q["question_text"].lower())[:80]
            if fp not in seen_fp:
                seen_fp.add(fp)
                uniq.append(dict(q, question_type=qtype))
        out.extend(_sample(uniq + [qb.gen_number_series(rng) for _ in range(count)], count, rng))

    elif qtype == "aptitude_verbal":
        pool = [dict(q, question_type=qtype) for q in qb.VERBAL_CURATED]
        out.extend(_sample(pool, count, rng))

    elif qtype == "code_output":
        pool = []
        for q in qb.OUTPUT_PREDICTION:
            if diffs and q["difficulty"] not in diffs:
                continue
            pool.append({
                "question_type": "code_output",
                "skill": {"python": "Python", "javascript": "JavaScript", "sql": "SQL"}.get(q.get("language", ""), q.get("language", "General")),
                "topic": q["topic"],
                "difficulty": q["difficulty"],
                "question_text": (
                    f"What will be the output of the following {q['language']} code?\n\n"
                    f"```\n{q['snippet']}\n```"
                ),
                "content": {"snippet": q["snippet"], "language": q["language"], "editor_language": None},
                "correct_answer": {"output": q["output"]},
                "explanation": q["explanation"],
                "estimated_time_seconds": 120,
            })
        out.extend(_sample(pool, count, rng))

    elif qtype == "debugging":
        pool = []
        for q in qb.DEBUG_QUESTIONS:
            if diffs and q["difficulty"] not in diffs:
                continue
            pool.append({
                "question_type": "debugging",
                "skill": q["skill"],
                "topic": q["topic"],
                "difficulty": q["difficulty"],
                "question_text": (
                    f"{q['question_text']}\n\n```\n{q['buggy_code']}\n```"
                ),
                "content": {"buggy_code": q["buggy_code"], "editor_language": None},
                "correct_answer": {"keywords": q["correct_answer"]["keywords"]},
                "explanation": q.get("explanation"),
                "estimated_time_seconds": 420,
            })
        out.extend(_sample(pool, count, rng))

    return out


def _build_coding(section: dict, rng: random.Random) -> list[dict]:
    count = section["count"]
    skills = [s.lower() for s in (section.get("skills") or [])]
    diffs = _difficulties(section.get("difficulty", "medium"))
    out: list[dict] = []

    runnable: list[dict] = []
    for d in diffs:
        runnable.extend(qb.CODING_PROBLEMS.get(d, []))
    if section.get("difficulty", "medium") == "mixed":
        runnable = sum((qb.CODING_PROBLEMS[d] for d in ("easy", "medium", "hard")), [])
    picked = _sample(runnable, min(count, 3) * max(count, 1), rng)

    conceptual: list[dict] = []
    for lang in ("javascript", "java"):
        if any(lang in s or s in lang for s in skills):
            conceptual.extend(qb.CODING_CONCEPTUAL.get(lang, []))

    merged = ([dict(c, question_type="coding", _difficulty=c.get("difficulty", "medium"))
               for c in conceptual] +
              [dict(p, question_type="coding", _difficulty=p.get("difficulty", "medium"))
               for p in picked])
    rng.shuffle(merged)
    for q in merged:
        if len(out) >= count:
            break
        diff = q.pop("_difficulty", "medium") if "_difficulty" in q else "medium"
        content = {
            "starter_code": q.get("starter_code"),
            "language": q.get("language", "python"),
            "function_name": None,
            "description": q.get("description"),
            "test_cases": q.get("test_cases", []),
            "keywords": q.get("keywords"),
            "reference_solution": q.get("reference_solution"),
        }
        text = f"{q['title']}\n\n{q['description']}"
        if content["language"] == "python" and content["test_cases"]:
            ref = (content.get("reference_solution") or "")
            fn_name = ref.split("def ")[1].split("(")[0].strip() if "def " in ref else None
            content["function_name"] = fn_name
        out.append({
            "question_type": "coding",
            "skill": q.get("topics", ["Coding"])[0].title() if q.get("topics") else "Coding",
            "topic": ", ".join(q.get("topics", [])) or "General",
            "difficulty": diff,
            "question_text": text,
            "content": content,
            "correct_answer": {"reference_solution": content.get("reference_solution")},
            "explanation": None,
            "estimated_time_seconds": {"easy": 600, "medium": 900, "hard": 1500}.get(diff, 900),
        })
    return out


def _build_sql_query(section: dict, rng: random.Random) -> list[dict]:
    diffs = _difficulties(section.get("difficulty", "medium"))
    pool = [dict(q, question_type=section["question_type"])
            for q in qb.SQL_QUESTIONS if q["difficulty"] in diffs] or \
           [dict(q, question_type=section["question_type"]) for q in qb.SQL_QUESTIONS]
    picked = _sample(pool, section["count"], rng)
    return [
        {
            "question_type": section["question_type"],
            "skill": "SQL",
            "topic": q["topic"],
            "difficulty": q["difficulty"],
            "question_text": (
                f"{q['question_text']}\n\nSample schema:\n"
                "departments(id, name)\nemployees(id, name, department_id, salary, hired_year)"
            ),
            "content": {
                "schema_statements": qb.SQL_SCHEMA_STATEMENTS,
                "reference_query": q["reference_query"],
                "editor_language": "sql",
            },
            "correct_answer": {"reference_query": q["reference_query"]},
            "explanation": None,
            "estimated_time_seconds": 300,
        }
        for q in picked
    ]


def _build_subjective(section: dict, rng: random.Random,
                      candidate_ctx: dict | None) -> list[dict]:
    qtype = section["question_type"]
    count = section["count"]
    diffs = _difficulties(section.get("difficulty", "medium"))

    if qtype == "system_design":
        pool = []
        for d in diffs:
            pool.extend([dict(p, skill="System Design", topic="System Design", difficulty=d)
                         for p in qb.SYSTEM_DESIGN_PROMPTS.get(d, [])])
        items = _sample(pool or [x for lst in qb.SYSTEM_DESIGN_PROMPTS.values() for x in lst], count, rng)
        return [{
            "question_type": qtype,
            "skill": "System Design",
            "topic": "System Design",
            "difficulty": q["difficulty"],
            "question_text": q["prompt"],
            "content": {},
            "correct_answer": {"rubric": q["rubric"]},
            "explanation": None,
            "estimated_time_seconds": 900,
        } for q in items]

    bank_map = {
        "scenario": qb.SCENARIO_BANK,
        "case_study": qb.CASE_STUDY_BANK,
        "situational_judgment": qb.SITUATIONAL_JUDGMENT_BANK,
    }
    if qtype in bank_map:
        pool = [dict(q, question_type=qtype) for q in bank_map[qtype]
                if not diffs or q["difficulty"] in diffs]
        out = _sample(pool, count, rng)
        while len(out) < count:
            out.extend(_sample([dict(q, question_type=qtype) for q in bank_map[qtype]],
                               count - len(out), rng))
        return [{
            "question_type": qtype,
            "skill": q["skill"],
            "topic": q["topic"],
            "difficulty": q["difficulty"],
            "question_text": q["question_text"],
            "content": {},
            "correct_answer": {"rubric": q["rubric"]},
            "explanation": None,
            "estimated_time_seconds": 600,
        } for q in out]

    if qtype in {"resume_based", "project_based"}:
        ctx = candidate_ctx or {}
        pool = qb.build_resume_questions(
            projects=ctx.get("projects", []),
            skills=ctx.get("skills", []),
            experiences=ctx.get("experience", []),
        )
        pool = [dict(q, question_type=qtype) for q in pool] or [dict(
            question_type=qtype, skill="General", topic="Experience", difficulty="medium",
            question_text=(
                "Describe the most technically challenging project you have built: architecture, "
                "trade-offs, failure modes and how you would scale it."
            ),
            correct_answer={"rubric": ["architecture", "challenge", "trade-off", "scale"]},
            estimated_time_seconds=600,
        )]
        return [{
            "question_type": qtype,
            "skill": q.get("skill", "General"),
            "topic": q.get("topic", "Resume"),
            "difficulty": q.get("difficulty", "medium"),
            "question_text": q["question_text"],
            "content": {},
            "correct_answer": {"rubric": (q.get("correct_answer") or {}).get("rubric", [])},
            "explanation": None,
            "estimated_time_seconds": q.get("estimated_time_seconds", 600),
        } for q in _sample(pool, count, rng)]

    if qtype == "behavioral":
        pool: list[dict] = []
        for d in diffs or ["medium"]:
            pool.extend(qb.behavioral_pool(d))
        return [{
            "question_type": qtype,
            "skill": q["skill"],
            "topic": q["topic"],
            "difficulty": q["difficulty"],
            "question_text": q["question_text"],
            "content": {},
            "correct_answer": {"rubric": (q.get("correct_answer") or {}).get("rubric", q.get("rubric"))},
            "explanation": None,
            "estimated_time_seconds": 300,
        } for q in _sample(pool, count, rng)]

    raise ValueError(f"Unsupported subjective type {qtype}")


SECTION_BUILDERS = {
    "objective": _build_objective,
    "coding": _build_coding,
    "sql_query": _build_sql_query,
    "sql_debug": lambda s, r: _build_sql_query(s, r),
}


def _builder_for(qtype: str):
    if qtype in _MCQ_SHAPED or qtype.startswith("aptitude_") or qtype == "code_output":
        return lambda s, r: _build_objective(s, r)
    if qtype == "coding":
        return _build_coding
    if qtype == "sql_query":
        return _build_sql_query
    if qtype == "behavioral" or qtype in {
        "system_design", "scenario", "case_study", "resume_based",
        "project_based", "situational_judgment", "database_design",
    }:
        return lambda s, r: _build_subjective(s, r, None)
    if qtype == "debugging":
        return lambda s, r: _build_objective(s, r)
    raise ValueError(f"No builder for question type '{qtype}'")


def generate_assessment_questions(
    sections: list[dict],
    seed: int | None = None,
    candidate_ctx: dict | None = None,
) -> list[dict]:
    """Generate + validate the full question paper.

    Each ``sections`` item: {question_type, count, skills?, difficulty?,
    points_per_question?, time_limit_seconds?}.
    """
    rng = random.Random(seed)
    raw: list[dict] = []
    for section in sections:
        qtype = section["question_type"]
        if qtype in {"system_design", "scenario", "case_study", "resume_based",
                     "project_based", "situational_judgment", "database_design",
                     "behavioral"}:
            built = _build_subjective(section, rng, candidate_ctx)
        else:
            built = _builder_for(qtype)(section, rng)
        pts = float(section.get("points_per_question", 1.0))
        tlimit = section.get("time_limit_seconds")
        for q in built:
            q["points"] = pts
            if tlimit:
                q["estimated_time_seconds"] = tlimit
        raw.extend(built)

    clean = sanitize_batch(raw)
    rng.shuffle(clean)
    return clean


def subjective_builder_with_ctx(candidate_ctx: dict):
    def _b(section: dict, rng: random.Random) -> list[dict]:
        return _build_subjective(section, rng, candidate_ctx)
    return _b
