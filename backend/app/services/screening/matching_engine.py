from __future__ import annotations

import logging
import re
from typing import Any

from app.services.screening.skill_graph import SkillGraph

logger = logging.getLogger(__name__)

# ─── Sentence-Transformers Embedding Engine ────────────────────────────
# Lazy-loaded singleton for semantic similarity. Uses a small, fast model
# (all-MiniLM-L6-v2: 80MB, 384-dim) that runs on CPU in <10ms per pair.
# Falls back to Jaccard + SkillGraph when unavailable or on first import.


class _EmbeddingEngine:
    """Thread-safe lazy singleton for sentence-transformers embeddings."""

    _model = None
    _load_attempted = False

    @classmethod
    def _get_model(cls):
        if cls._load_attempted and cls._model is None:
            return None
        if cls._model is not None:
            return cls._model
        cls._load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info(
                "Loaded sentence-transformers model: all-MiniLM-L6-v2"
            )
            return cls._model
        except Exception as exc:
            logger.warning(
                "sentence-transformers unavailable, falling back to Jaccard+SkillGraph: %s",
                exc,
            )
            return None

    @classmethod
    def embed(cls, texts: list[str]):
        """Return embeddings for a list of texts, or None if model unavailable."""
        model = cls._get_model()
        if model is None:
            return None
        return model.encode(texts, convert_to_tensor=True)

    @classmethod
    def cosine_similarity(cls, emb_a, emb_b) -> float:
        """Compute cosine similarity between two embedding tensors."""
        if emb_a is None or emb_b is None:
            return 0.0
        import torch
        return float(torch.nn.functional.cosine_similarity(emb_a, emb_b, dim=0).item())

    @classmethod
    def batch_cosine(cls, emb_a, emb_b) -> list[float]:
        """Compute pairwise cosine similarity between two sets of embeddings."""
        if emb_a is None or emb_b is None:
            return []
        import torch
        return torch.nn.functional.cosine_similarity(emb_a, emb_b, dim=1).tolist()


class MatchingEngine:
    """Matching engine with sentence-transformers semantic similarity.

    Uses weighted scoring, embedding-based text similarity (sentence-transformers),
    fuzzy skill matching via the SkillGraph, and transferable skill detection
    to evaluate candidate-JD fit. Falls back to Jaccard + n-gram when the
    embedding model is unavailable.
    """

    SKILL_SYNONYMS: dict[str, list[str]] = SkillGraph.SYNONYMS

    # ─── Skill Matching ──────────────────────────────────────────────

    @staticmethod
    def normalize_skill(skill: str) -> str:
        return re.sub(r"[\s\-_]+", " ", skill.lower().strip())

    @classmethod
    def skill_matches(cls, candidate_skill: str, required_skill: str) -> bool:
        cs = cls.normalize_skill(candidate_skill)
        rs = cls.normalize_skill(required_skill)
        if cs == rs or rs in cs or cs in rs:
            return True
        synonyms = cls.SKILL_SYNONYMS.get(rs, [])
        for syn in synonyms:
            if cs == syn or syn in cs:
                return True
        if SkillGraph.are_synonyms(candidate_skill, required_skill):
            return True
        if SkillGraph.similarity_score(candidate_skill, required_skill) >= 0.65:
            return True
        return False

    @classmethod
    def calculate_skill_match(
        cls,
        candidate_skills: list[str],
        required_skills: list[str],
        preferred_skills: list[str] | None = None,
    ) -> tuple[int, list[str], list[str], list[str]]:
        """Returns (score 0-100, matched, missing_required, missing_preferred)."""
        if not required_skills and not preferred_skills:
            return 100, candidate_skills, [], []

        matched: list[str] = []
        missing_required: list[str] = []
        for req in required_skills:
            found = any(cls.skill_matches(cs, req) for cs in candidate_skills)
            if found:
                matched.append(req)
            else:
                missing_required.append(req)

        missing_preferred: list[str] = []
        if preferred_skills:
            for pref in preferred_skills:
                found = any(cls.skill_matches(cs, pref) for cs in candidate_skills)
                if found:
                    matched.append(pref)
                else:
                    missing_preferred.append(pref)

        req_weight = 0.8
        pref_weight = 0.2
        req_count = max(len(required_skills), 1)
        pref_count = max(len(preferred_skills or []), 1)
        req_score = (len(matched[:len(required_skills)]) / req_count) * 100 * req_weight
        pref_score = 0.0
        if preferred_skills:
            pref_matched = len(matched) - len(matched[:len(required_skills)])
            pref_score = (pref_matched / pref_count) * 100 * pref_weight
        score = int(min(req_score + pref_score, 100))
        return score, matched, missing_required, missing_preferred

    # ─── Experience Matching ─────────────────────────────────────────

    @staticmethod
    def parse_experience_years(experience_str: str | None) -> float:
        if not experience_str:
            return 0.0
        nums = re.findall(r"(\d+(?:\.\d+)?)", experience_str)
        if nums:
            return max(float(n) for n in nums)
        return 0.0

    @staticmethod
    def calculate_experience_match(
        candidate_years: float, required_str: str | None,
    ) -> int:
        if not required_str or required_str.strip() == "":
            return 80
        required_years = MatchingEngine.parse_experience_years(required_str)
        if required_years <= 0:
            return 80
        if candidate_years >= required_years:
            return 100
        ratio = candidate_years / required_years
        if ratio >= 0.8:
            return 85
        if ratio >= 0.5:
            return 60
        if ratio >= 0.3:
            return 40
        return 20

    # ─── Education Matching ──────────────────────────────────────────

    DEGREE_HIERARCHY: dict[str, int] = {
        "high school": 1,
        "diploma": 2,
        "associate": 3,
        "bachelor": 4,
        "b.tech": 4,
        "b.sc": 4,
        "b.e": 4,
        "be": 4,
        "bs": 4,
        "master": 5,
        "m.sc": 5,
        "m.tech": 5,
        "mca": 5,
        "mba": 5,
        "ma": 5,
        "me": 5,
        "phd": 6,
        "doctorate": 6,
        "doctoral": 6,
    }

    @classmethod
    def _degree_level(cls, degree_str: str) -> int:
        degree_lower = degree_str.lower()
        for key, level in cls.DEGREE_HIERARCHY.items():
            if key in degree_lower:
                return level
        return 3

    @classmethod
    def calculate_education_match(
        cls,
        candidate_degrees: list[str],
        required_education: str | None,
    ) -> int:
        if not required_education or required_education.strip() == "":
            return 80
        if not candidate_degrees:
            return 20
        required_level = cls._degree_level(required_education)
        candidate_max = max(cls._degree_level(d) for d in candidate_degrees)
        if candidate_max >= required_level:
            return 100
        diff = required_level - candidate_max
        if diff == 1:
            return 65
        return 30

    # ─── Project Matching ────────────────────────────────────────────

    @staticmethod
    def calculate_project_match(
        project_count: int, technologies_used: list[str], jd_skills: list[str],
    ) -> int:
        if project_count == 0:
            return 10
        score = min(project_count * 15, 60)
        if technologies_used and jd_skills:
            tech_overlap = sum(
                1 for t in technologies_used
                if any(MatchingEngine.skill_matches(t, s) for s in jd_skills)
            )
            score += min(int((tech_overlap / max(len(jd_skills), 1)) * 40), 40)
        return min(score, 100)

    # ─── Certification Matching ──────────────────────────────────────

    @staticmethod
    def calculate_certification_match(
        candidate_certs: list[str], jd_relevant_certs: list[str] | None,
    ) -> int:
        if not jd_relevant_certs:
            return 70
        if not candidate_certs:
            return 15
        matched = sum(
            1 for jc in candidate_certs
            if any(MatchingEngine.skill_matches(jc, r) for r in jd_relevant_certs)
        )
        return min(int((matched / max(len(jd_relevant_certs), 1)) * 100), 100)

    # ─── Location Matching ───────────────────────────────────────────

    @staticmethod
    def calculate_location_match(
        candidate_location: str | None, job_location: str,
    ) -> int:
        if not candidate_location:
            return 60
        job_lower = job_location.lower()
        cand_lower = candidate_location.lower()
        if "remote" in job_lower:
            return 100
        if cand_lower == job_lower:
            return 100
        cand_city = cand_lower.split(",")[0].strip()
        job_city = job_lower.split(",")[0].strip()
        if cand_city == job_city:
            return 100
        cand_country = cand_lower.split(",")[-1].strip()
        job_country = job_lower.split(",")[-1].strip()
        if cand_country == job_country:
            return 70
        return 30

    # ─── Employment Type Matching ────────────────────────────────────

    @staticmethod
    def calculate_employment_type_match(
        candidate_preference: str | None, job_type: str,
    ) -> int:
        if not candidate_preference:
            return 70
        if candidate_preference.lower() == job_type.lower():
            return 100
        return 40

    # ─── Semantic Text Similarity ────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [w for w in re.findall(r"\b[a-z0-9+#]+\b", text.lower()) if len(w) > 1]

    @classmethod
    def calculate_semantic_similarity(cls, text_a: str, text_b: str) -> int:
        """Calculate semantic similarity between two text blocks.

        Uses sentence-transformers embeddings when available, blended with
        Jaccard, n-gram, and SkillGraph features. Falls back to algorithmic
        similarity when the embedding model is not loaded.
        """
        if not text_a.strip() or not text_b.strip():
            return 30
        tokens_a = set(cls._tokenize(text_a))
        tokens_b = set(cls._tokenize(text_b))
        if not tokens_a or not tokens_b:
            return 0
        # --- Algorithmic features (always available) ---
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / max(len(union), 1)
        bigrams_a = cls._bigrams(tokens_a)
        bigrams_b = cls._bigrams(tokens_b)
        bigram_inter = bigrams_a & bigrams_b
        bigram_union = bigrams_a | bigrams_b
        bigram_sim = len(bigram_inter) / max(len(bigram_union), 1)
        semantic_bonus = 0.0
        skills_a = SkillGraph.extract_skills_from_text(text_a)
        skills_b = SkillGraph.extract_skills_from_text(text_b)
        if skills_a and skills_b:
            matched_pairs = 0
            for sa in skills_a:
                for sb in skills_b:
                    sim = SkillGraph.similarity_score(sa, sb)
                    if sim >= 0.50:
                        matched_pairs += sim
            semantic_bonus = min(matched_pairs / max(len(skills_a), 1), 0.3)
        # --- Embedding similarity (when model available) ---
        emb_sim = _EmbeddingEngine.batch_cosine(
            _EmbeddingEngine.embed([text_a[:2000]]),
            _EmbeddingEngine.embed([text_b[:2000]]),
        )
        if emb_sim:
            embedding_score = emb_sim[0]
            # Blend: 40% embedding + 30% Jaccard + 20% bigram + 10% SkillGraph
            combined = (
                0.40 * embedding_score
                + 0.30 * jaccard
                + 0.20 * bigram_sim
                + 0.10 * semantic_bonus
            )
        else:
            # Fallback: no embedding model available
            combined = 0.50 * jaccard + 0.30 * bigram_sim + 0.20 * semantic_bonus
        return int(min(combined * 140, 100))

    @staticmethod
    def _bigrams(tokens: set[str]) -> set[tuple[str, str]]:
        token_list = sorted(tokens)
        return {(token_list[i], token_list[i + 1]) for i in range(len(token_list) - 1)}

    # ─── Composite Score ─────────────────────────────────────────────

    @staticmethod
    def calculate_overall_score(
        skill: int,
        experience: int,
        education: int,
        project: int,
        certification: int,
        location: int,
        employment_type: int,
        semantic: int,
        weights: dict[str, float] | None = None,
    ) -> int:
        if weights is None:
            weights = {
                "skills": 0.30,
                "experience": 0.20,
                "education": 0.15,
                "projects": 0.10,
                "certifications": 0.10,
                "location": 0.05,
                "employment_type": 0.05,
                "semantic": 0.05,
            }
        score = (
            skill * weights.get("skills", 0.30)
            + experience * weights.get("experience", 0.20)
            + education * weights.get("education", 0.15)
            + project * weights.get("projects", 0.10)
            + certification * weights.get("certifications", 0.10)
            + location * weights.get("location", 0.05)
            + employment_type * weights.get("employment_type", 0.05)
            + semantic * weights.get("semantic", 0.05)
        )
        return int(min(max(score, 0), 100))

    # ─── Strengths / Weaknesses / Recommendation ─────────────────────

    @staticmethod
    def identify_strengths(scores: dict[str, int], matched_skills: list[str]) -> list[str]:
        strengths: list[str] = []
        if scores.get("skill", 0) >= 80:
            strengths.append("Strong skill alignment with the job requirements")
        if scores.get("experience", 0) >= 80:
            strengths.append("Experience level meets or exceeds requirements")
        if scores.get("education", 0) >= 80:
            strengths.append("Education background is well-aligned")
        if scores.get("project", 0) >= 70:
            strengths.append("Relevant project experience demonstrates practical skills")
        if scores.get("certification", 0) >= 70:
            strengths.append("Relevant certifications add credibility")
        if len(matched_skills) >= 5:
            strengths.append(f"Matches {len(matched_skills)} required/preferred skills")
        if scores.get("semantic", 0) >= 60:
            strengths.append("Resume content aligns well with job description")
        if not strengths:
            strengths.append("Some areas of the profile are relevant to this role")
        return strengths

    @staticmethod
    def identify_weaknesses(
        scores: dict[str, int],
        missing_required: list[str],
        missing_preferred: list[str],
    ) -> list[str]:
        weaknesses: list[str] = []
        if missing_required:
            weaknesses.append(f"Missing required skills: {', '.join(missing_required[:5])}")
        if missing_preferred:
            weaknesses.append(f"Missing preferred skills: {', '.join(missing_preferred[:3])}")
        if scores.get("experience", 0) < 50:
            weaknesses.append("Experience level is below job requirements")
        if scores.get("education", 0) < 50:
            weaknesses.append("Education level does not meet job requirements")
        if scores.get("skill", 0) < 50:
            weaknesses.append("Significant skill gaps detected")
        if scores.get("project", 0) < 30:
            weaknesses.append("Limited relevant project experience")
        if not weaknesses:
            weaknesses.append("Minor gaps in certain areas")
        return weaknesses

    @staticmethod
    def determine_recommendation(overall_score: int) -> str:
        if overall_score >= 80:
            return "strongly_recommend"
        if overall_score >= 65:
            return "recommend"
        if overall_score >= 45:
            return "consider"
        return "not_recommended"

    @staticmethod
    def determine_strength_level(overall_score: int) -> str:
        if overall_score >= 80:
            return "excellent"
        if overall_score >= 65:
            return "good"
        if overall_score >= 45:
            return "average"
        return "low"

    # ─── Enhanced Skill Matching with SkillGraph ──────────────────────

    @classmethod
    def calculate_skill_match_enhanced(
        cls,
        candidate_skills: list[str],
        required_skills: list[str],
        preferred_skills: list[str] | None = None,
    ) -> tuple[int, list[str], list[str], list[str], list[str], dict[str, float]]:
        """Enhanced skill matching with embedding-based transferable detection.

        Returns (score, matched, missing_required, missing_preferred, transferable, similarity_map).
        Uses sentence-transformers embeddings when available for more accurate
        semantic skill similarity; falls back to SkillGraph fuzzy matching.
        """
        if not required_skills and not preferred_skills:
            return 100, candidate_skills, [], [], [], {}

        matched: list[str] = []
        missing_required: list[str] = []
        transferable: list[str] = []
        similarity_map: dict[str, float] = {}

        # --- Embedding-based similarity (if model available) ---
        emb_cache: dict[str, Any] = {}
        all_skills = list(set(candidate_skills + required_skills + (preferred_skills or [])))
        if all_skills:
            embeddings = _EmbeddingEngine.embed(all_skills)
            if embeddings is not None:
                for i, s in enumerate(all_skills):
                    emb_cache[s.lower()] = embeddings[i]

        for req in required_skills:
            found = False
            best_sim = 0.0
            best_match = ""
            for cs in candidate_skills:
                if cls.skill_matches(cs, req):
                    found = True
                    sim = SkillGraph.similarity_score(cs, req)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = cs
                    break
                else:
                    # Try embedding similarity
                    cs_emb = emb_cache.get(cs.lower())
                    req_emb = emb_cache.get(req.lower())
                    if cs_emb is not None and req_emb is not None:
                        sim = _EmbeddingEngine.cosine_similarity(cs_emb, req_emb)
                    else:
                        sim = SkillGraph.similarity_score(cs, req)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = cs
            if found:
                matched.append(req)
                similarity_map[req] = best_sim if best_match else 1.0
            elif best_sim >= 0.55:
                transferable.append(req)
                similarity_map[req] = best_sim
            else:
                missing_required.append(req)

        missing_preferred: list[str] = []
        if preferred_skills:
            for pref in preferred_skills:
                found = False
                for cs in candidate_skills:
                    if cls.skill_matches(cs, pref):
                        found = True
                        cs_emb = emb_cache.get(cs.lower())
                        pref_emb = emb_cache.get(pref.lower())
                        if cs_emb is not None and pref_emb is not None:
                            similarity_map[pref] = _EmbeddingEngine.cosine_similarity(cs_emb, pref_emb)
                        else:
                            similarity_map[pref] = SkillGraph.similarity_score(cs, pref)
                        break
                    else:
                        cs_emb = emb_cache.get(cs.lower())
                        pref_emb = emb_cache.get(pref.lower())
                        if cs_emb is not None and pref_emb is not None:
                            sim = _EmbeddingEngine.cosine_similarity(cs_emb, pref_emb)
                        else:
                            sim = SkillGraph.similarity_score(cs, pref)
                        if sim >= 0.55:
                            similarity_map[pref] = sim
                if found:
                    matched.append(pref)
                else:
                    missing_preferred.append(pref)

        req_weight = 0.75
        pref_weight = 0.15
        transfer_weight = 0.10
        req_count = max(len(required_skills), 1)
        pref_count = max(len(preferred_skills or []), 1)
        req_score = (len(matched[:len(required_skills)]) / req_count) * 100 * req_weight
        transfer_bonus = (len(transferable) / req_count) * 100 * transfer_weight
        pref_score = 0.0
        if preferred_skills:
            pref_matched = len(matched) - len(matched[:len(required_skills)])
            pref_score = (pref_matched / pref_count) * 100 * pref_weight
        score = int(min(req_score + pref_score + transfer_bonus, 100))
        return score, matched, missing_required, missing_preferred, transferable, similarity_map

    # ─── Hiring Confidence Score ──────────────────────────────────────

    @staticmethod
    def calculate_hiring_confidence(
        overall_score: int,
        matched_count: int,
        total_required: int,
        experience_score: int,
        education_score: int,
    ) -> int:
        """Calculate a confidence score (0-100) for the hiring recommendation."""
        if total_required == 0:
            skill_confidence = 80
        else:
            skill_confidence = (matched_count / total_required) * 100
        base_confidence = 0.40 * overall_score + 0.25 * skill_confidence + 0.20 * experience_score + 0.15 * education_score
        if overall_score >= 80:
            base_confidence = min(base_confidence + 5, 100)
        elif overall_score < 40:
            base_confidence = max(base_confidence - 5, 0)
        return int(min(max(base_confidence, 0), 100))

    # ─── AI Search Relevance ──────────────────────────────────────────

    @classmethod
    def calculate_search_relevance(
        cls,
        candidate_skills: list[str],
        query_skills: list[str],
        candidate_years: float,
        query_years: float | None,
        candidate_location: str | None,
        query_location: str | None,
    ) -> int:
        """Calculate how well a candidate matches a parsed search query."""
        if not query_skills:
            skill_score = 60
        else:
            matched = 0
            for qs in query_skills:
                if any(cls.skill_matches(cs, qs) for cs in candidate_skills):
                    matched += 1
                elif any(SkillGraph.similarity_score(cs, qs) >= 0.55 for cs in candidate_skills):
                    matched += 0.6
            skill_score = int(min((matched / max(len(query_skills), 1)) * 100, 100))

        if query_years and query_years > 0:
            if candidate_years >= query_years:
                exp_score = 100
            elif candidate_years >= query_years * 0.8:
                exp_score = 80
            elif candidate_years >= query_years * 0.5:
                exp_score = 50
            else:
                exp_score = 20
        else:
            exp_score = 70

        if query_location and candidate_location:
            loc_score = cls.calculate_location_match(candidate_location, query_location)
        else:
            loc_score = 70

        return int(0.50 * skill_score + 0.30 * exp_score + 0.20 * loc_score)
