import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

SECTION_WEIGHTS: dict[str, int] = {
    "personal_info": 10,
    "education": 15,
    "experience": 30,
    "skills": 20,
    "projects": 10,
    "certifications": 10,
    "languages": 5,
}

RECOMMENDED_SECTIONS = [
    "personal_info",
    "education",
    "experience",
    "skills",
    "projects",
]

ATS_KEYWORDS: list[str] = [
    "achieved", "improved", "trained", "managed", "created",
    "developed", "implemented", "designed", "led", "increased",
    "decreased", "reduced", "generated", "delivered", "launched",
    "optimized", "streamlined", "mentored", "coordinated", "established",
    "result", "outcome", "metric", "percent", "dollar", "saved",
    "team", "project", "budget", "revenue", "client",
]

INDUSTRY_TRENDING_KEYWORDS: dict[str, list[str]] = {
    "python": ["fastapi", "pytest", "async", "docker", "kubernetes", "mlops", "ci/cd", "terraform"],
    "javascript": ["typescript", "react", "next.js", "node.js", "graphql", "tailwind", "jest", "playwright"],
    "java": ["spring boot", "microservices", "jpa", "kafka", "docker", "kubernetes", "aws"],
    "data_science": ["machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "sql", "tableau", "power bi"],
    "devops": ["docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions", "prometheus", "grafana"],
    "cloud": ["aws", "azure", "gcp", "serverless", "lambda", "s3", "ec2", "cloudformation"],
}

ESSENTIAL_SKILLS_BY_ROLE: dict[str, list[str]] = {
    "software_engineer": ["git", "algorithms", "data structures", "api", "testing", "sql", "problem solving"],
    "frontend": ["html", "css", "javascript", "typescript", "react", "responsive design", "version control"],
    "backend": ["api", "database", "authentication", "caching", "testing", "security", "docker"],
    "data_scientist": ["python", "sql", "statistics", "machine learning", "data visualization", "feature engineering"],
    "devops": ["linux", "docker", "kubernetes", "ci/cd", "monitoring", "infrastructure as code", "cloud"],
    "product_manager": ["roadmapping", "user research", "agile", "analytics", "a/b testing", "stakeholder management"],
}


class ResumeAnalysisEngine:
    @staticmethod
    def analyze(parsed_data: dict[str, Any], file_type: str = "pdf") -> dict[str, Any]:
        sections = {
            "personal_info": bool(parsed_data.get("personal_info", {})),
            "education": bool(parsed_data.get("education", [])),
            "experience": bool(parsed_data.get("experience", [])),
            "skills": bool(parsed_data.get("skills", [])),
            "projects": bool(parsed_data.get("projects", [])),
            "certifications": bool(parsed_data.get("certifications", [])),
            "languages": bool(parsed_data.get("languages", [])),
        }

        section_scores: dict[str, int] = {}
        for section_name, present in sections.items():
            weight = SECTION_WEIGHTS.get(section_name, 5)
            section_scores[section_name] = weight if present else 0

        quality_score = sum(section_scores.values())
        missing_sections = [
            s for s in RECOMMENDED_SECTIONS if not sections.get(s)
        ]

        raw_text = parsed_data.get("raw_text", "")
        extracted_skills = parsed_data.get("skills", [])
        skill_names = [s.get("name", s.get("skill", "")).lower() for s in (extracted_skills or []) if isinstance(s, dict)]

        completeness_score = ResumeAnalysisEngine._calculate_completeness_score(parsed_data)
        readability_score = ResumeAnalysisEngine._calculate_readability_score(raw_text)
        professionalism_score = ResumeAnalysisEngine._calculate_professionalism_score(raw_text, sections)
        keyword_optimization_score = ResumeAnalysisEngine._calculate_keyword_optimization_score(raw_text, skill_names)
        ats_score = ResumeAnalysisEngine._calculate_ats_score(raw_text, parsed_data)
        keyword_analysis = ResumeAnalysisEngine._analyze_keywords(raw_text, sections)
        formatting_issues = ResumeAnalysisEngine._check_formatting(raw_text, file_type)
        skill_analysis = ResumeAnalysisEngine._analyze_skills(extracted_skills, raw_text)
        industry_keywords = ResumeAnalysisEngine._generate_industry_keywords(skill_names)

        recommendations = ResumeAnalysisEngine._generate_recommendations(
            sections=sections,
            missing_sections=missing_sections,
            quality_score=quality_score,
            readability_score=readability_score,
            professionalism_score=professionalism_score,
            keyword_optimization_score=keyword_optimization_score,
            ats_score=ats_score,
            formatting_issues=formatting_issues,
            skill_analysis=skill_analysis,
            raw_text=raw_text,
        )

        return {
            "quality_score": quality_score,
            "completeness_score": completeness_score,
            "readability_score": readability_score,
            "professionalism_score": professionalism_score,
            "keyword_optimization_score": keyword_optimization_score,
            "ats_score": ats_score,
            "missing_sections": missing_sections,
            "recommendations": recommendations,
            "section_scores": section_scores,
            "keyword_analysis": keyword_analysis,
            "formatting_issues": formatting_issues,
            "skill_analysis": skill_analysis,
            "industry_keywords": industry_keywords,
            "strengths": ResumeAnalysisEngine._identify_strengths(
                sections=sections,
                quality_score=quality_score,
                readability_score=readability_score,
                professionalism_score=professionalism_score,
                ats_score=ats_score,
                skill_analysis=skill_analysis,
            ),
            "weaknesses": ResumeAnalysisEngine._identify_weaknesses(
                missing_sections=missing_sections,
                quality_score=quality_score,
                readability_score=readability_score,
                professionalism_score=professionalism_score,
                ats_score=ats_score,
                formatting_issues=formatting_issues,
                skill_analysis=skill_analysis,
            ),
        }

    @staticmethod
    def _calculate_completeness_score(parsed_data: dict[str, Any]) -> int:
        score = 0
        total = 0

        pi = parsed_data.get("personal_info", {}) or {}
        pi_fields = ["name", "email", "phone", "location"]
        pi_present = sum(1 for f in pi_fields if pi.get(f))
        total += len(pi_fields)
        score += pi_present

        for section in ("education", "experience", "projects", "certifications"):
            items = parsed_data.get(section, []) or []
            total += min(len(items), 5)
            score += min(len(items), 5)

        skills = parsed_data.get("skills", []) or []
        total += 5
        score += min(len(skills), 5)

        return int((score / max(total, 1)) * 100)

    @staticmethod
    def _calculate_readability_score(text: str) -> int:
        if not text.strip():
            return 0

        score = 50
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return 20

        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if 10 <= avg_sentence_length <= 25:
            score += 20
        elif avg_sentence_length < 10:
            score += 10
        else:
            score += 5

        bullet_points = len(re.findall(r'[•\-\*]\s+', text))
        if bullet_points >= 5:
            score += 15
        elif bullet_points >= 2:
            score += 10

        paragraphs = [p for p in text.split('\n\n') if len(p.strip()) > 30]
        if 3 <= len(paragraphs) <= 10:
            score += 15

        return min(score, 100)

    @staticmethod
    def _calculate_professionalism_score(text: str, sections: dict[str, bool]) -> int:
        if not text.strip():
            return 0

        score = 30
        text_lower = text.lower()

        action_verb_count = sum(1 for kw in ATS_KEYWORDS if kw.lower() in text_lower)
        score += min(action_verb_count * 5, 20)

        has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text))
        if has_email:
            score += 10

        has_phone = bool(re.search(r'[\+\d\s\-\(\)]{7,}', text))
        if has_phone:
            score += 5

        has_linkedin = 'linkedin' in text_lower
        if has_linkedin:
            score += 5

        has_github = 'github' in text_lower
        if has_github:
            score += 5

        quantifiable = len(re.findall(r'\d+%|\$\d+|\d+x|\d+ years|\d+ people', text_lower))
        score += min(quantifiable * 5, 20)

        return min(score, 100)

    @staticmethod
    def _calculate_keyword_optimization_score(text: str, skill_names: list[str]) -> int:
        if not text.strip():
            return 0

        score = 30
        text_lower = text.lower()

        ats_matched = sum(1 for kw in ATS_KEYWORDS if kw.lower() in text_lower)
        score += min(ats_matched * 5, 25)

        skill_in_text = sum(1 for s in skill_names if s in text_lower)
        score += min(skill_in_text * 3, 20)

        industry_keywords_found = 0
        for category, keywords in INDUSTRY_TRENDING_KEYWORDS.items():
            industry_keywords_found += sum(1 for kw in keywords if kw.lower() in text_lower)
        score += min(industry_keywords_found * 3, 25)

        return min(score, 100)

    @staticmethod
    def _calculate_ats_score(text: str, parsed_data: dict[str, Any]) -> int:
        score = 30

        if not text.strip():
            return 0

        text_lower = text.lower()
        action_keywords_found = sum(1 for kw in ATS_KEYWORDS if kw.lower() in text_lower)
        score += min(action_keywords_found * 5, 20)

        sections_present = sum(1 for s in RECOMMENDED_SECTIONS if parsed_data.get(s))
        score += sections_present * 5

        has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text))
        if has_email:
            score += 5

        has_phone = bool(re.search(r'[\+\d\s\-\(\)]{7,}', text))
        if has_phone:
            score += 5

        lines = text.split('\n')
        if 30 <= len(lines) <= 80:
            score += 10
        elif len(lines) > 80:
            score += 5

        quantifiable = len(re.findall(r'\d+%|\$\d+|\d+x', text_lower))
        score += min(quantifiable * 5, 15)

        has_section_headers = any(header in text_lower for header in
                                   ["experience", "education", "skills", "summary", "objective"])
        if has_section_headers:
            score += 10

        return min(score, 100)

    @staticmethod
    def _analyze_keywords(text: str, sections: dict[str, bool]) -> dict[str, Any]:
        text_lower = text.lower()

        action_keywords_found: list[str] = []
        action_keywords_missing: list[str] = []

        for kw in ATS_KEYWORDS:
            if kw.lower() in text_lower:
                action_keywords_found.append(kw)
            else:
                action_keywords_missing.append(kw)

        keyword_density: dict[str, int] = {}
        words = re.findall(r'\b[a-z]+\b', text_lower)
        for kw in ATS_KEYWORDS:
            count = words.count(kw.lower())
            if count > 0:
                keyword_density[kw] = count

        return {
            "action_keywords_found": action_keywords_found,
            "action_keywords_missing": action_keywords_missing[:10],
            "total_action_keywords": len(ATS_KEYWORDS),
            "matched_action_keywords": len(action_keywords_found),
            "keyword_density": keyword_density,
        }

    @staticmethod
    def _check_formatting(text: str, file_type: str = "pdf") -> list[str]:
        issues: list[str] = []
        if len(text) < 100:
            issues.append("Resume content appears too short")
        lines = text.split("\n")
        if len(lines) < 10:
            issues.append("Resume has very few lines of content")
        long_lines = [l for l in lines if len(l) > 200]
        if long_lines:
            issues.append(f"Found {len(long_lines)} line(s) that are very long (>200 chars)")
        contact_patterns = ["@", "linkedin", "github"]
        has_contact = any(p in text.lower() for p in contact_patterns)
        if not has_contact:
            issues.append("No contact information (email, LinkedIn, or GitHub) detected")
        if file_type and file_type.lower() not in ("pdf", "docx"):
            issues.append(f"File format '{file_type}' may not be ATS-friendly; PDF or DOCX recommended")
        total_lines = len(lines)
        if total_lines > 100:
            issues.append("Resume is too long (over 100 lines); consider condensing to 1-2 pages")
        elif total_lines < 20:
            issues.append("Resume is very short; consider adding more details")
        return issues

    @staticmethod
    def _analyze_skills(extracted_skills: list | None, raw_text: str) -> dict[str, Any]:
        skills = extracted_skills or []
        skill_names = []
        for s in skills:
            if isinstance(s, dict):
                name = s.get("name", s.get("skill", ""))
            elif isinstance(s, str):
                name = s
            else:
                continue
            skill_names.append(name)

        text_lower = raw_text.lower()

        categorized: dict[str, list[str]] = {}
        for s in skill_names:
            s_lower = s.lower()
            matched = False
            for category, keywords in INDUSTRY_TRENDING_KEYWORDS.items():
                if s_lower in keywords or any(kw == s_lower for kw in keywords):
                    categorized.setdefault(category, []).append(s)
                    matched = True
            if not matched:
                categorized.setdefault("other", []).append(s)

        duplicates = []
        seen = set()
        for s in skill_names:
            s_lower = s.lower()
            if s_lower in seen:
                duplicates.append(s)
            seen.add(s_lower)

        missing_essential: list[str] = []
        role_skills_found: set[str] = set()
        for role, essentials in ESSENTIAL_SKILLS_BY_ROLE.items():
            found = [e for e in essentials if e.lower() in text_lower or e.lower() in seen]
            role_skills_found.update(found)
            role_missing = [e for e in essentials if e.lower() not in text_lower and e.lower() not in seen]
            if role_missing and len(found) >= 2:
                missing_essential.extend(role_missing)

        missing_essential = list(set(missing_essential))

        suggestions: list[str] = []
        for s in skill_names:
            s_lower = s.lower()
            for category, related in INDUSTRY_TRENDING_KEYWORDS.items():
                if s_lower in related:
                    trending = [kw for kw in related if kw.lower() not in text_lower and kw.lower() not in seen]
                    suggestions.extend(trending[:3])
                    break

        suggestions = list(set(suggestions))[:10]

        return {
            "skill_names": list(set(skill_names)),
            "total_skills": len(set(skill_names)),
            "categorized": categorized,
            "duplicates": duplicates,
            "missing_essential": missing_essential,
            "suggestions": suggestions,
        }

    @staticmethod
    def _generate_industry_keywords(skill_names: list[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for category, keywords in INDUSTRY_TRENDING_KEYWORDS.items():
            matched = [kw for kw in keywords if kw.lower() in [s.lower() for s in skill_names]]
            if matched:
                suggested = [kw for kw in keywords if kw not in matched]
                result[category] = {
                    "matched": matched,
                    "suggested": suggested[:5],
                }
        return result

    @staticmethod
    def _identify_strengths(
        sections: dict[str, bool],
        quality_score: int,
        readability_score: int,
        professionalism_score: int,
        ats_score: int,
        skill_analysis: dict[str, Any],
    ) -> list[str]:
        strengths: list[str] = []
        if quality_score >= 80:
            strengths.append("Well-structured resume with all key sections present")
        if readability_score >= 70:
            strengths.append("Good readability with clear sentence structure")
        if professionalism_score >= 70:
            strengths.append("Professional presentation with action verbs and contact info")
        if ats_score >= 70:
            strengths.append("Strong ATS compatibility score")
        if sections.get("experience"):
            strengths.append("Work experience section included")
        if sections.get("projects"):
            strengths.append("Projects section demonstrates practical skills")
        if skill_analysis.get("total_skills", 0) >= 10:
            strengths.append(f"Strong skill set with {skill_analysis['total_skills']} skills identified")
        if not skill_analysis.get("duplicates"):
            strengths.append("No duplicate skills found")
        return strengths

    @staticmethod
    def _identify_weaknesses(
        missing_sections: list[str],
        quality_score: int,
        readability_score: int,
        professionalism_score: int,
        ats_score: int,
        formatting_issues: list[str],
        skill_analysis: dict[str, Any],
    ) -> list[str]:
        weaknesses: list[str] = []
        for section in missing_sections:
            label = section.replace("_", " ").title()
            weaknesses.append(f"Missing {label} section")
        if quality_score < 60:
            weaknesses.append("Overall resume quality needs improvement")
        if readability_score < 50:
            weaknesses.append("Resume readability needs improvement; use shorter sentences and bullet points")
        if professionalism_score < 50:
            weaknesses.append("Add more action verbs and quantifiable achievements")
        if ats_score < 50:
            weaknesses.append("ATS compatibility is low; add more industry keywords")
        for issue in formatting_issues:
            weaknesses.append(issue)
        if skill_analysis.get("duplicates"):
            weaknesses.append(f"Duplicate skills found: {', '.join(skill_analysis['duplicates'][:3])}")
        if skill_analysis.get("missing_essential"):
            weaknesses.append(f"Missing essential skills: {', '.join(skill_analysis['missing_essential'][:5])}")
        if skill_analysis.get("total_skills", 0) < 5:
            weaknesses.append("Very few skills identified; consider adding more")
        return weaknesses[:10]

    @staticmethod
    def _generate_recommendations(
        sections: dict[str, bool],
        missing_sections: list[str],
        quality_score: int,
        readability_score: int,
        professionalism_score: int,
        keyword_optimization_score: int,
        ats_score: int,
        formatting_issues: list[str],
        skill_analysis: dict[str, Any],
        raw_text: str,
    ) -> list[str]:
        recommendations: list[str] = []

        if not sections.get("experience"):
            recommendations.append("Add a work experience section with your job history, responsibilities, and achievements")
        if not sections.get("skills"):
            recommendations.append("Include a skills section listing your technical and soft skills")
        if not sections.get("projects"):
            recommendations.append("Add projects to demonstrate practical experience and problem-solving abilities")
        if not sections.get("education"):
            recommendations.append("Include your educational background with degree, institution, and graduation year")
        if not sections.get("certifications"):
            recommendations.append("Consider adding relevant certifications to boost credibility")
        if not sections.get("languages"):
            recommendations.append("Listing additional languages can be beneficial for global roles")

        if readability_score < 60:
            recommendations.append("Improve readability: use bullet points, keep sentences under 25 words, and add section headers")
        if professionalism_score < 60:
            recommendations.append("Enhance professionalism: add quantifiable achievements (%, $, metrics) and action verbs throughout")
        if keyword_optimization_score < 50:
            recommendations.append("Include more industry-specific keywords and action verbs to improve keyword optimization")
        if ats_score < 60:
            recommendations.append("Improve ATS compatibility: use standard section headers, include relevant keywords from job descriptions")

        for issue in formatting_issues:
            recommendations.append(issue)

        if skill_analysis.get("missing_essential"):
            skills_str = ", ".join(skill_analysis["missing_essential"][:5])
            recommendations.append(f"Consider adding these essential skills: {skills_str}")
        if skill_analysis.get("duplicates"):
            recommendations.append("Remove duplicate skill entries to keep your resume clean and focused")
        if skill_analysis.get("suggestions"):
            trending = ", ".join(skill_analysis["suggestions"][:5])
            recommendations.append(f"Trending skills to consider: {trending}")

        if quality_score < 50:
            recommendations.append("Use a professional resume template to ensure proper structure and formatting")

        action_verb_count = sum(1 for kw in ATS_KEYWORDS if kw.lower() in raw_text.lower())
        if action_verb_count < 8:
            recommendations.append(f"Use more action verbs (currently found {action_verb_count}/31 recommended)")
            recommendations.append("Start bullet points with strong action verbs like 'Developed', 'Implemented', 'Optimized'")

        has_quantifiable = bool(re.findall(r'\d+%|\$\d+|\d+x', raw_text.lower()))
        if not has_quantifiable:
            recommendations.append("Add quantifiable achievements (percentages, dollar amounts, metrics) to strengthen impact")

        return recommendations[:15]
