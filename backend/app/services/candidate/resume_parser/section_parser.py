import re

SECTION_PATTERNS: list[tuple[str, str, str]] = [
    ("personal_info", r"(?:personal\s*information|personal\s*details|contact|profile|summary|about\s*me)", "i"),
    ("education", r"(?:education|academic\s*background|academic\s*qualifications|qualifications|degrees)", "i"),
    ("experience", r"(?:experience|work\s*experience|employment|employment\s*history|professional\s*experience|work\s*history|career)", "i"),
    ("skills", r"(?:skills|technical\s*skills|core\s*competencies|competencies|expertise|technologies|tech\s*stack)", "i"),
    ("projects", r"(?:projects|personal\s*projects|academic\s*projects|key\s*projects|side\s*projects)", "i"),
    ("certifications", r"(?:certifications|certificates|certification|licenses|credentials)", "i"),
    ("languages", r"(?:languages|language\s*proficiency)", "i"),
    ("achievements", r"(?:achievements|awards|honors|recognition|accomplishments)", "i"),
    ("publications", r"(?:publications|papers|research|research\s*papers)", "i"),
    ("references", r"(?:references|professional\s*references)", "i"),
    ("objective", r"(?:objective|career\s*objective|professional\s*summary)", "i"),
    ("interests", r"(?:interests|hobbies|activities)", "i"),
]


class SectionParser:
    SECTION_HEADERS: list[str] = [
        "education", "experience", "work experience", "employment",
        "skills", "technical skills", "core competencies", "expertise",
        "projects", "personal projects", "academic projects",
        "certifications", "certificates", "licenses",
        "languages", "language proficiency",
        "achievements", "awards", "honors", "recognition",
        "publications", "papers", "research",
        "references", "professional references",
        "objective", "career objective", "professional summary",
        "interests", "hobbies", "activities",
        "personal information", "personal details", "contact", "profile", "summary", "about me",
    ]

    @staticmethod
    def detect_sections(text: str) -> dict[str, str]:
        lines = text.split("\n")
        sections: dict[str, str] = {
            "personal_info": "",
            "education": "",
            "experience": "",
            "skills": "",
            "projects": "",
            "certifications": "",
            "languages": "",
            "other": "",
        }
        current_section: str = "personal_info"
        current_content: list[str] = []

        for line in lines:
            stripped = line.strip()
            detected = SectionParser._match_section(stripped)
            if detected:
                sections[current_section] = "\n".join(current_content).strip()
                current_section = detected
                current_content = []
            else:
                if stripped:
                    current_content.append(stripped)

        sections[current_section] = "\n".join(current_content).strip()
        return {k: v for k, v in sections.items() if v.strip()}

    @staticmethod
    def _match_section(line: str) -> str | None:
        clean = re.sub(r"^[#*•\-_=\s]+|[#*•\-_=\s]+$", "", line).strip().lower()
        for section_name, pattern, flags in SECTION_PATTERNS:
            if re.fullmatch(pattern, clean, flags=re.IGNORECASE if "i" in flags else 0):
                return section_name
        return None

    @staticmethod
    def extract_bullet_points(text: str) -> list[str]:
        bullets: list[str] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if re.match(r"^[\s]*[•\-\*→▶–‣⁃○▪▸▹►▪➢➤・]+", line):
                bullets.append(re.sub(r"^[\s]*[•\-\*→▶–‣⁃○▪▸▹►▪➢➤・]+\s*", "", line))
            elif re.match(r"^\s*\d+[\.\)]\s*", line):
                bullets.append(re.sub(r"^\s*\d+[\.\)]\s*", "", line))
        return bullets

    @staticmethod
    def extract_date_range(text: str) -> tuple[str | None, str | None]:
        date_patterns = [
            r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*\d{4}",
            r"\d{4}",
        ]

        combined = "|".join(date_patterns)
        pattern = rf"((?:{combined})\s*(?:[-–to]+\s*)(?:{combined}|present|current|now|till\s*date))|(?:({combined})\s*[-–]\s*({combined}|present|current|now))"
        dates = re.findall(pattern, text, re.IGNORECASE)
        if dates:
            match = dates[0]
            groups = [g for g in match if g]
            if len(groups) >= 2:
                start, end = groups[0], groups[1]
            else:
                parts = re.split(r"\s*[-–to]+\s*", groups[0], maxsplit=1)
                start = parts[0] if len(parts) > 0 else None
                end = parts[1] if len(parts) > 1 else None
            return start, end

        single_dates = re.findall(r"\b(19|20)\d{2}\b", text)
        if len(single_dates) >= 2:
            return single_dates[0], single_dates[-1]
        elif single_dates:
            return single_dates[0], single_dates[0]

        return None, None
