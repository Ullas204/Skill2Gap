"""Phase 12 – Adaptive difficulty engine.

Ladder: easy → medium → hard → expert.
Two consecutive correct answers step UP; a wrong answer steps DOWN.
"""

from __future__ import annotations

DIFFICULTY_LADDER = ["easy", "medium", "hard", "expert"]


def next_difficulty(current: str, was_correct: bool, streak: int) -> str:
    """Compute the difficulty for the NEXT question.

    ``streak`` is the count of consecutive correct answers INCLUDING the
    answer just given.
    """
    if current not in DIFFICULTY_LADDER:
        current = "medium"
    idx = DIFFICULTY_LADDER.index(current)
    if not was_correct:
        return DIFFICULTY_LADDER[max(idx - 1, 0)]
    if streak >= 2:
        return DIFFICULTY_LADDER[min(idx + 1, len(DIFFICULTY_LADDER) - 1)]
    return DIFFICULTY_LADDER[idx]


def pick_next_question(
    pool: list[dict],
    answered_ids: set[str],
    current_difficulty: str,
    last_correct: bool | None,
    streak: int,
    adaptive: bool,
) -> dict | None:
    """Choose the next question from the remaining pool.

    Non-adaptive: first unanswered question in order.
    Adaptive: prefer questions at ``next_difficulty``; fall back to the
    nearest available difficulties so the assessment never stalls.
    """
    remaining = [q for q in pool if str(q["id"]) not in answered_ids]
    if not remaining:
        return None
    if not adaptive:
        ordered = sorted(remaining, key=lambda q: q.get("order_index", 0))
        return ordered[0]

    base = current_difficulty if last_correct is None else next_difficulty(
        current_difficulty, bool(last_correct), streak
    )
    try:
        target_idx = DIFFICULTY_LADDER.index(base)
    except ValueError:
        target_idx = 1

    def _dist(q: dict) -> int:
        d = (q.get("difficulty") or "medium").lower()
        qi = DIFFICULTY_LADDER.index(d) if d in DIFFICULTY_LADDER else 1
        return abs(qi - target_idx)

    remaining.sort(key=_dist)
    return remaining[0]


def starting_difficulty(pool: list[dict]) -> str:
    counts: dict[str, int] = {}
    for q in pool:
        d = (q.get("difficulty") or "medium").lower()
        counts[d] = counts.get(d, 0) + 1
    for d in ("easy", "medium", "hard"):
        if counts.get(d):
            return d
    return "medium"
