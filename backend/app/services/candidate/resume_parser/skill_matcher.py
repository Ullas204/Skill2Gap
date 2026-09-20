import re
from typing import Any

from app.services.candidate.resume_parser.skill_database import SKILL_LOOKUP


class SkillMatcher:
    @staticmethod
    def extract_skills(text: str) -> list[dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        lower_text = text.lower()
        words = set(re.findall(r"[a-zA-Z#+.]+(?:[-/][a-zA-Z#+.]+)*", lower_text))

        for word in words:
            clean = word.strip()
            if clean in SKILL_LOOKUP:
                canonical = SKILL_LOOKUP[clean]
                if canonical not in found:
                    found[canonical] = {
                        "name": canonical,
                        "matched_on": clean,
                        "category": SkillMatcher._get_category(canonical),
                    }

        for phrase_length in range(6, 1, -1):
            lines = lower_text.split("\n")
            for line in lines:
                words_in_line = line.split()
                for i in range(len(words_in_line) - phrase_length + 1):
                    phrase = " ".join(words_in_line[i : i + phrase_length])
                    if phrase in SKILL_LOOKUP:
                        canonical = SKILL_LOOKUP[phrase]
                        if canonical not in found:
                            found[canonical] = {
                                "name": canonical,
                                "matched_on": phrase,
                                "category": SkillMatcher._get_category(canonical),
                            }

        return list(found.values())

    @staticmethod
    def extract_skills_from_sections(sections: dict[str, str]) -> list[dict[str, Any]]:
        all_skills: dict[str, dict[str, Any]] = {}

        skills_text = sections.get("skills", "")
        if skills_text:
            for skill in SkillMatcher.extract_skills(skills_text):
                all_skills[skill["name"]] = skill

        other_sections = {
            k: v for k, v in sections.items() if k != "skills" and v.strip()
        }
        for section_text in other_sections.values():
            for skill in SkillMatcher.extract_skills(section_text):
                if skill["name"] not in all_skills:
                    skill["inferred"] = True
                    if "context" not in skill:
                        skill["context"] = section_text[:100]
                    all_skills[skill["name"]] = skill

        return list(all_skills.values())

    @staticmethod
    def _get_category(skill_name: str) -> str:
        from app.services.candidate.resume_parser.skill_database import SKILL_DATABASE

        for category, skills in SKILL_DATABASE.items():
            for skill in skills:
                if skill["name"].lower() == skill_name.lower():
                    return category
        return "other"

    @staticmethod
    def calculate_skill_score(
        required_skills: list[str], extracted_skills: list[dict[str, Any]]
    ) -> tuple[float, list[str], list[str]]:
        extracted_names = {s["name"].lower() for s in extracted_skills}
        matched: list[str] = []
        missing: list[str] = []

        for skill in required_skills:
            if any(
                skill.lower() == ext_name or
                (skill.lower() in SKILL_LOOKUP and SKILL_LOOKUP[skill.lower()] in extracted_names)
                for ext_name in extracted_names
            ):
                matched.append(skill)
            else:
                missing.append(skill)

        score = (len(matched) / len(required_skills) * 100) if required_skills else 100
        return round(score, 1), matched, missing
