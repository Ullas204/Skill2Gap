"""Deterministic post-processing for extracted personal info.

The legacy ``PersonalInfoExtractor`` regexes sometimes capture digit runs
inside emails ("nagu22022002@gmail.com" -> phone "22022002") or treat the
email domain as a website. This module filters such artifacts without touching
the legacy extractor: candidates are only dropped, never invented.
"""

from __future__ import annotations

import re

_PHONE_MIN_DIGITS = 10
_PHONE_MAX_DIGITS = 13


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _is_plausible_phone(candidate: str) -> bool:
    digits = _digits(candidate)
    if not _PHONE_MIN_DIGITS <= len(digits) <= _PHONE_MAX_DIGITS:
        return False
    # Sequences of a single repeated digit are never real phone numbers.
    if len(set(digits)) == 1:
        return False
    return True


def _looks_like_website(candidate: str, email: str | None) -> bool:
    value = (candidate or "").strip()
    if not value or "@" in value:
        return False
    if not re.search(r"\.[a-zA-Z]{2,}(?:/|$)", value):
        return False
    if email and "@" in email:
        domain = email.rsplit("@", 1)[-1].lower().strip()
        if domain and value.lower().rstrip("/") == domain:
            return False  # just the email provider domain
    return True


def sanitize_personal_info(info: dict | None) -> dict | None:
    """Return a cleaned copy of *info*; drops implausible contact values."""
    if not info:
        return info
    cleaned = dict(info)

    email = cleaned.get("email")
    email_str = str(email).strip() if email else None
    email_digits = _digits(email_str) if email_str else ""

    def _iter_candidates(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(v) for v in value]
        return [p.strip() for p in re.split(r"[,;/]", str(value)) if p.strip()]

    raw_main = cleaned.get("phone")
    candidates = _iter_candidates(raw_main)
    for alt_key in ("alternate_phones", "alternate_phone", "other_phones"):
        candidates.extend(_iter_candidates(cleaned.get(alt_key)))

    valid: list[str] = []
    seen_digits: set[str] = set()
    for cand in candidates:
        digits = _digits(cand)
        if not _is_plausible_phone(cand):
            continue
        if email_digits and digits and digits in email_digits:
            continue  # digit run lifted out of the email address
        if digits in seen_digits:
            continue
        seen_digits.add(digits)
        valid.append(cand.strip())

    if valid:
        # Prefer the most complete number as the primary phone.
        main = max(valid, key=lambda c: len(_digits(c)))
        cleaned["phone"] = main
        alternates = [c for c in valid if c != main]
        if alternates:
            cleaned["alternate_phones"] = alternates
        else:
            cleaned.pop("alternate_phones", None)
            cleaned.pop("alternate_phone", None)
            cleaned.pop("other_phones", None)
    else:
        cleaned.pop("phone", None)
        cleaned.pop("alternate_phones", None)
        cleaned.pop("alternate_phone", None)
        cleaned.pop("other_phones", None)

    website = cleaned.get("website")
    if website and not _looks_like_website(str(website), email_str):
        cleaned.pop("website", None)

    return cleaned
