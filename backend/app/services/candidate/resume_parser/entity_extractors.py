import re
from typing import Any


class PersonalInfoExtractor:
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_PATTERNS = [
        re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"),
        re.compile(r"\+\d{1,3}\s\d{1,3}\s\d{3,4}\s\d{3,4}"),
    ]
    LINKEDIN_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?", re.IGNORECASE
    )
    GITHUB_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?", re.IGNORECASE
    )
    WEBSITE_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[a-zA-Z0-9_./-]*)?"
    )
    NAME_PATTERN = re.compile(
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$", re.MULTILINE
    )

    @classmethod
    def extract(cls, text: str, section_text: str = "") -> dict[str, Any]:
        info: dict[str, Any] = {}
        combined = f"{section_text}\n{text}" if section_text else text
        first_lines = [l.strip() for l in text.strip().split("\n")[:5] if l.strip()]

        name = cls._extract_name(first_lines)
        if name:
            info["name"] = name

        emails = cls.EMAIL_PATTERN.findall(combined)
        if emails:
            info["email"] = emails[0]

        phones = cls._extract_phone(combined)
        if phones:
            info["phone"] = phones[0]
            if len(phones) > 1:
                info["alternate_phones"] = phones[1:]

        linkedin = cls.LINKEDIN_PATTERN.findall(combined)
        if linkedin:
            info["linkedin"] = linkedin[0]

        github = cls.GITHUB_PATTERN.findall(combined)
        if github:
            info["github"] = github[0]

        urls: list[str] = []
        for match in cls.WEBSITE_PATTERN.finditer(combined):
            url = match.group(0)
            if not any(
                keyword in url.lower()
                for keyword in ["linkedin", "github", "email"]
            ):
                urls.append(url)
        if urls:
            info["website"] = urls[0]
            if len(urls) > 1:
                info["additional_urls"] = urls[1:]

        location = cls._extract_location(first_lines, combined)
        if location:
            info["location"] = location

        return info

    @classmethod
    def _extract_name(cls, first_lines: list[str]) -> str | None:
        for line in first_lines[:3]:
            match = cls.NAME_PATTERN.match(line)
            if match:
                name = match.group(1)
                if (
                    len(name) > 3
                    and len(name.split()) >= 2
                    and "resume" not in name.lower()
                    and "curriculum" not in name.lower()
                ):
                    return name
        return None

    @classmethod
    def _extract_phone(cls, text: str) -> list[str]:
        phones: list[str] = []
        for pattern in cls.PHONE_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                cleaned = re.sub(r"[^\d+]", "", match)
                if 7 <= len(cleaned) <= 15 and cleaned not in phones:
                    phones.append(cleaned)
        return phones

    @classmethod
    def _extract_location(cls, first_lines: list[str], text: str) -> str | None:
        location_keywords = [
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}\b",
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",
        ]
        for line in first_lines[:10]:
            for pattern in location_keywords:
                match = re.search(pattern, line)
                if match:
                    return match.group(0)
        return None


class EducationExtractor:
    DEGREE_PATTERNS = re.compile(
        r"(?:"
        r"B\.?(?:S|A|E|Tech|Sc|Com|BA|Eng|Arch|Pharm|Ed)|"
        r"M\.?(?:S|A|E|Tech|Sc|Com|BA|Eng|Arch|Pharm|Ed|B\.?A)|"
        r"Ph\.?D|MBA|M\.?B\.?A|B\.?B\.?A|BBA|"
        r"Bachelor(?:'s)?\s*(?:of|in|of\s+Science\s+in|of\s+Arts\s+in|of\s+Technology|of\s+Engineering)?|"
        r"Master(?:'s)?\s*(?:of|in|of\s+Science\s+in|of\s+Arts\s+in|of\s+Business\s+Administration)?|"
        r"Doctor(?:ate)?|"
        r"Associate(?:'s)?\s*(?:degree|of|in)?|"
        r"High\s*School|"
        r"12(?:th)?\s*(?:grade|standard|pass)?|"
        r"10(?:th)?\s*(?:grade|standard|pass)?|"
        r"Diploma|"
        r"B\.?Com|M\.?Com|"
        r"B\.?Sc|M\.?Sc|"
        r"BCA|MCA|"
        r"B\.?Tech|M\.?Tech"
        r")",
        re.IGNORECASE,
    )

    INSTITUTION_PATTERNS = re.compile(
        r"(?:"
        r"University|College|Institute|School|Academy|"
        r"IIT|NIT|IIIT|MIT|Stanford|Harvard|Oxford|Cambridge|"
        r"Indian\s+Institute|National\s+Institute"
        r")",
        re.IGNORECASE,
    )

    @classmethod
    def extract(cls, section_text: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        blocks = cls._split_into_blocks(section_text)

        for block in blocks:
            entry: dict[str, Any] = {}
            degree = cls._extract_degree(block)
            if degree:
                entry["degree"] = degree

            institution = cls._extract_institution(block)
            if institution:
                entry["institution"] = institution

            dates = cls._extract_dates(block)
            if dates:
                entry.update(dates)

            gpa = cls._extract_gpa(block)
            if gpa:
                entry["gpa"] = gpa

            field = cls._extract_field(block, entry.get("degree", ""))
            if field:
                entry["field"] = field

            if entry and ("degree" in entry or "institution" in entry):
                entry["raw_text"] = block.strip()
                entries.append(entry)

        return entries

    @classmethod
    def _split_into_blocks(cls, text: str) -> list[str]:
        lines = text.strip().split("\n")
        blocks: list[str] = []
        current: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current:
                    blocks.append("\n".join(current))
                    current = []
            else:
                current.append(stripped)

        if current:
            blocks.append("\n".join(current))
        return blocks

    @classmethod
    def _extract_degree(cls, text: str) -> str | None:
        match = cls.DEGREE_PATTERNS.search(text)
        if match:
            degree = match.group(0).strip()
            return degree
        return None

    @classmethod
    def _extract_institution(cls, text: str) -> str | None:
        match = cls.INSTITUTION_PATTERNS.search(text)
        if match:
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]
            lines = context.split("\n")
            for line in lines:
                line = line.strip()
                if cls.INSTITUTION_PATTERNS.search(line):
                    return line
        return None

    @classmethod
    def _extract_dates(cls, text: str) -> dict[str, str | None] | None:
        from app.services.candidate.resume_parser.section_parser import SectionParser
        start, end = SectionParser.extract_date_range(text)
        if start or end:
            return {"start_date": start, "end_date": end}
        return None

    @classmethod
    def _extract_gpa(cls, text: str) -> str | None:
        gpa_pattern = re.compile(
            r"(?:GPA|CGPA|grade\s*point|g\.?p\.?a\.?)\s*:?\s*(\d+\.?\d*)",
            re.IGNORECASE,
        )
        match = gpa_pattern.search(text)
        if match:
            return match.group(1)
        return None

    @classmethod
    def _extract_field(cls, text: str, degree: str) -> str | None:
        field_keywords = [
            "Computer Science", "Engineering", "Business Administration",
            "Information Technology", "Data Science", "Mathematics",
            "Physics", "Chemistry", "Biology", "Commerce",
            "Arts", "Economics", "Finance", "Marketing",
            "Psychology", "Communications", "Design",
        ]
        lower = text.lower()
        for field in field_keywords:
            if field.lower() in lower:
                return field
        return None


class ExperienceExtractor:
    @classmethod
    def extract(cls, section_text: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        blocks = cls._split_into_blocks(section_text)

        for block in blocks:
            entry: dict[str, Any] = {}

            title = cls._extract_title(block)
            if title:
                entry["title"] = title

            company = cls._extract_company(block)
            if company:
                entry["company"] = company

            dates = cls._extract_dates(block)
            if dates:
                entry.update(dates)

            description = cls._extract_description(block, entry)
            if description:
                entry["description"] = description

            if entry and ("title" in entry or "company" in entry):
                entry["raw_text"] = block.strip()
                entries.append(entry)

        return entries

    @classmethod
    def _split_into_blocks(cls, text: str) -> list[str]:
        lines = text.strip().split("\n")
        blocks: list[str] = []
        current: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current:
                    blocks.append("\n".join(current))
                    current = []
            else:
                current.append(stripped)
        if current:
            blocks.append("\n".join(current))
        return blocks

    @classmethod
    def _extract_title(cls, text: str) -> str | None:
        title_keywords = [
            "Engineer", "Developer", "Manager", "Director", "Lead",
            "Architect", "Analyst", "Consultant", "Specialist",
            "Coordinator", "Administrator", "Officer", "Head",
            "Intern", "Associate", "Senior", "Junior", "Principal",
            "SDE", "Software", "Full Stack", "Frontend", "Backend",
            "DevOps", "Data", "Machine Learning", "AI",
            "Product", "Project", "Program", "Technical",
            "Engineering", "Research", "Scientist",
        ]
        pattern = r"(?:^|\n)([A-Z][a-zA-Z\s,]+(?:{patterns})[a-zA-Z\s,/&]+)"
        combined = "|".join(title_keywords)
        full_pattern = pattern.format(patterns=combined)
        match = re.search(full_pattern, text, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            if len(title) < 80 and len(title) > 2:
                return title.split("\n")[0].strip()
        return None

    @classmethod
    def _extract_company(cls, text: str) -> str | None:
        company_keywords = [
            r"(?:at|@|–|—)\s+([A-Z][a-zA-Z0-9\s,.]{2,60})",
            r"(?:^|\n)([A-Z][a-zA-Z0-9\s,.]{2,60})\s*(?:–|—|-|\|)",
            r"(?:^|\n)([A-Z][a-zA-Z0-9\s,.]{2,60})\s*$",
        ]
        for pattern in company_keywords:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                company = match.group(1).strip().rstrip(",")
                if len(company) > 2 and not any(
                    kw in company.lower()
                    for kw in ["experience", "employment", "work history"]
                ):
                    return company
        return None

    @classmethod
    def _extract_dates(cls, text: str) -> dict[str, str | None] | None:
        from app.services.candidate.resume_parser.section_parser import SectionParser
        start, end = SectionParser.extract_date_range(text)
        if start or end:
            return {"start_date": start, "end_date": end}
        return None

    @classmethod
    def _extract_description(cls, text: str, entry: dict) -> list[str] | None:
        from app.services.candidate.resume_parser.section_parser import SectionParser
        bullets = SectionParser.extract_bullet_points(text)
        if bullets:
            return bullets
        lines = text.strip().split("\n")
        title_line_count = 2 if entry.get("title") else 1
        remaining = [l.strip() for l in lines[title_line_count:] if l.strip()]
        return remaining if remaining else None


class ProjectExtractor:
    @classmethod
    def extract(cls, section_text: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        blocks = section_text.strip().split("\n\n")

        for block in blocks:
            lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
            if not lines:
                continue

            entry: dict[str, Any] = {}
            entry["name"] = lines[0]

            from app.services.candidate.resume_parser.section_parser import SectionParser
            start, end = SectionParser.extract_date_range(block)
            if start:
                entry["start_date"] = start
            if end:
                entry["end_date"] = end

            bullets = SectionParser.extract_bullet_points(block)
            if bullets:
                entry["description"] = bullets
            elif len(lines) > 1:
                entry["description"] = lines[1:]

            tech_pattern = re.findall(
                r"(?:technologies|tech\s*stack|tools|built\s*with|using)\s*:?\s*(.+?)(?:\n|$)",
                block,
                re.IGNORECASE,
            )
            if tech_pattern:
                entry["technologies"] = [t.strip() for t in tech_pattern[0].split(",")]

            if entry and "name" in entry:
                entries.append(entry)

        return entries


class CertificationExtractor:
    @classmethod
    def extract(cls, section_text: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        lines = [l.strip() for l in section_text.strip().split("\n") if l.strip()]

        cert_keywords = [
            "certified", "certification", "certificate", "license",
            "AWS", "Azure", "GCP", "PMP", "CISSP", "CISM", "CISA",
            "CISCO", "CCNA", "CCNP", "CCIE", "COMPTIA",
            "ITIL", "TOGAF", "SCJP", "OCJP", "OCP",
            "CPA", "CFA", "FRM", "PRM",
            "Six Sigma", "Lean", "Scrum", "CSM", "PSM",
            "Kubernetes", "CKA", "CKAD", "CKS",
            "Terraform", "Hashicorp",
            "Google", "Microsoft", "Oracle",
            "IELTS", "TOEFL", "GRE", "GMAT",
            "Red Hat", "RHCE", "RHCSA", "RHCA",
            "Salesforce", "ADMIN", "PD1",
            "CEH", "OSCP", "Security+",
        ]

        for line in lines:
            for keyword in cert_keywords:
                if keyword.lower() in line.lower():
                    entries.append({"name": line, "issuer": cls._extract_issuer(line)})
                    break

        return entries

    @classmethod
    def _extract_issuer(cls, text: str) -> str | None:
        issuers = [
            "AWS", "Amazon", "Azure", "Microsoft", "Google",
            "CISCO", "CompTIA", "PMP", "PMI", "Scrum Alliance",
            "Scrum.org", "SAFe", "Scaled Agile",
            "ISC2", "ISACA", "SANS", "EC-Council",
            "Oracle", "Red Hat", "Linux Foundation",
            "Salesforce", "IBM", "HashiCorp",
            "IELTS", "British Council", "ETS",
        ]
        for issuer in issuers:
            if issuer.lower() in text.lower():
                return issuer
        return None


class LanguageExtractor:
    @classmethod
    def extract(cls, section_text: str) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        lines = [l.strip() for l in section_text.strip().split("\n") if l.strip()]

        language_names = [
            "English", "Hindi", "Spanish", "French", "German",
            "Mandarin", "Chinese", "Japanese", "Korean",
            "Arabic", "Portuguese", "Russian", "Italian",
            "Dutch", "Turkish", "Polish", "Swedish", "Danish",
            "Norwegian", "Finnish", "Greek", "Hebrew",
            "Thai", "Vietnamese", "Bengali", "Urdu", "Punjabi",
            "Marathi", "Gujarati", "Tamil", "Telugu", "Kannada",
            "Malayalam",
        ]

        for line in lines:
            lower = line.lower()
            for lang in language_names:
                if lang.lower() in lower:
                    entry: dict[str, str] = {"language": lang}

                    proficiency_keywords = {
                        "native": "native",
                        "fluent": "fluent",
                        "proficient": "proficient",
                        "advanced": "advanced",
                        "intermediate": "intermediate",
                        "basic": "basic",
                        "elementary": "elementary",
                        "conversational": "conversational",
                        "beginner": "beginner",
                        "c2": "native", "c1": "advanced",
                        "b2": "upper_intermediate", "b1": "intermediate",
                        "a2": "elementary", "a1": "beginner",
                    }

                    for keyword, level in proficiency_keywords.items():
                        if keyword.lower() in lower:
                            entry["proficiency"] = level
                            break

                    if lang not in [e.get("language") for e in entries]:
                        entries.append(entry)
                    break

        return entries
