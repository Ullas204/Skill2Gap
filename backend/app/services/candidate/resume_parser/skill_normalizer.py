"""Skill normalization component (Phase 1).

Turns raw skill strings found anywhere in a resume into canonical
``NormalizedSkill`` objects:

    "Python 3"   -> Python            (Programming Language)
    "Postgres"   -> PostgreSQL        (Database)
    "React.js"   -> React             (Framework)
    "Fast API"   -> FastAPI           (Framework)

Deterministic dictionary-based normalization built on top of the existing
``SKILL_DATABASE`` (which stays untouched). No LLM calls, no fuzzy invention:
unknown tokens return ``None`` rather than a guessed skill.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .schemas import NormalizedSkill, SkillCategory
from .skill_database import SKILL_DATABASE

# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------

CATEGORY_MAP: dict[str, SkillCategory] = {
    "programming_languages": SkillCategory.PROGRAMMING_LANGUAGE,
    "frontend": SkillCategory.FRAMEWORK,
    "backend": SkillCategory.FRAMEWORK,
    "databases": SkillCategory.DATABASE,
    "cloud_devops": SkillCategory.DEVOPS,
    "data_ml": SkillCategory.AI_ML,
    "tools": SkillCategory.TOOL,
    "soft_skills": SkillCategory.SOFT_SKILL,
    "testing": SkillCategory.TESTING,
    "security": SkillCategory.SECURITY,
}

PER_NAME_CATEGORY: dict[str, SkillCategory] = {
    # Cloud platforms live under cloud_devops but deserve their own category.
    "aws": SkillCategory.CLOUD,
    "azure": SkillCategory.CLOUD,
    "gcp": SkillCategory.CLOUD,
    "amazon web services": SkillCategory.CLOUD,
    "google cloud platform": SkillCategory.CLOUD,
    "google cloud": SkillCategory.CLOUD,
    "microsoft azure": SkillCategory.CLOUD,
    # Data tooling under data_ml -> Data.
    "pandas": SkillCategory.DATA, "numpy": SkillCategory.DATA,
    "matplotlib": SkillCategory.DATA, "seaborn": SkillCategory.DATA,
    "plotly": SkillCategory.DATA, "tableau": SkillCategory.DATA,
    "power bi": SkillCategory.DATA, "looker": SkillCategory.DATA,
    "spark": SkillCategory.DATA, "hadoop": SkillCategory.DATA,
    "airflow": SkillCategory.DATA, "jupyter": SkillCategory.DATA,
    "sql": SkillCategory.DATABASE,
    "graphql": SkillCategory.FRAMEWORK,
    "microservices": SkillCategory.FRAMEWORK,
    "rest api": SkillCategory.TOOL, "restful api": SkillCategory.TOOL,
    "ci/cd": SkillCategory.DEVOPS,
    "machine learning": SkillCategory.AI_ML, "deep learning": SkillCategory.AI_ML,
    "natural language processing": SkillCategory.AI_ML, "nlp": SkillCategory.AI_ML,
    "computer vision": SkillCategory.AI_ML, "generative ai": SkillCategory.AI_ML,
    "llm": SkillCategory.AI_ML, "prompt engineering": SkillCategory.AI_ML,
    "leadership": SkillCategory.SOFT_SKILL, "communication": SkillCategory.SOFT_SKILL,
    "teamwork": SkillCategory.SOFT_SKILL, "problem solving": SkillCategory.SOFT_SKILL,
    "agile": SkillCategory.SOFT_SKILL,
}

# Extra dictionary entries merged on top of SKILL_DATABASE (same shape).
EXTRA_ENTRIES: dict[str, list[dict[str, object]]] = {
    "cloud_devops": [
        {"name": "ci/cd", "aliases": ["cicd", "ci cd", "continuous integration"]},
    ],
    "backend": [
        {"name": "rest api", "aliases": ["restful api", "rest apis", "restful apis", "restful web services"]},
        {"name": "microservices", "aliases": ["micro services", "microservice architecture"]},
    ],
    "data_ml": [
        {"name": "machine learning", "aliases": ["ml"]},
        {"name": "deep learning", "aliases": []},
        {"name": "natural language processing", "aliases": ["nlp"]},
        {"name": "computer vision", "aliases": []},
        {"name": "generative ai", "aliases": ["genai", "gen ai"]},
        {"name": "llm", "aliases": ["llms", "large language model", "large language models"]},
        {"name": "prompt engineering", "aliases": []},
    ],
}

# Canonical name -> proper display casing (everything else gets title-case).
DISPLAY_OVERRIDES: dict[str, str] = {
    "javascript": "JavaScript", "typescript": "TypeScript", "php": "PHP",
    "sql": "SQL", "html": "HTML", "css": "CSS", "scss": "SCSS", "less": "Less",
    "graphql": "GraphQL", "aws": "AWS", "gcp": "GCP", "azure": "Azure",
    "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "sqlite": "SQLite", "mariadb": "MariaDB", "elasticsearch": "Elasticsearch",
    "dynamodb": "DynamoDB", "neo4j": "Neo4j", "clickhouse": "ClickHouse",
    "influxdb": "InfluxDB", "supabase": "Supabase",
    "sql server": "SQL Server", "ibm db2": "IBM Db2",
    "next.js": "Next.js", "node.js": "Node.js", "d3.js": "D3.js",
    "chart.js": "Chart.js", "three.js": "Three.js", "vue": "Vue",
    "fastapi": "FastAPI",
    "tailwind": "Tailwind CSS", "tailwind css": "Tailwind CSS", "material ui": "Material UI",
    "chakra ui": "Chakra UI", "ant design": "Ant Design",
    "styled-components": "Styled Components",
    "numpy": "NumPy", "pandas": "Pandas", "scikit-learn": "scikit-learn",
    "opencv": "OpenCV", "nltk": "NLTK", "spacy": "spaCy",
    "hugging face": "Hugging Face", "langchain": "LangChain", "llama": "LLaMA",
    "openai": "OpenAI", "xgboost": "XGBoost", "lightgbm": "LightGBM",
    "power bi": "Power BI", "spark": "Apache Spark", "airflow": "Airflow",
    "mlflow": "MLflow", "kafka": "Kafka", "flink": "Flink",
    "rabbitmq": "RabbitMQ", "grpc": "gRPC", "oauth": "OAuth", "jwt": "JWT",
    "ssl/tls": "SSL/TLS", "saml": "SAML", "ldap": "LDAP", "siem": "SIEM",
    "owasp": "OWASP", "tdd": "TDD", "bdd": "BDD", "k6": "k6",
    "junit": "JUnit", "testng": "TestNG", "sonarqube": "SonarQube",
    "github actions": "GitHub Actions", "gitlab ci": "GitLab CI",
    "circleci": "CircleCI", "nginx": "NGINX", "new relic": "New Relic",
    "adobe xd": "Adobe XD", "unreal engine": "Unreal Engine",
    "monday.com": "Monday.com", "clickup": "ClickUp",
    "burp suite": "Burp Suite", "kali linux": "Kali Linux",
    "robot framework": "Robot Framework", "objective-c": "Objective-C",
    "powershell": "PowerShell", "ci/cd": "CI/CD", "rest api": "REST API",
    "microservices": "Microservices", "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "natural language processing": "Natural Language Processing",
    "computer vision": "Computer Vision", "generative ai": "Generative AI",
    "llm": "LLM", "prompt engineering": "Prompt Engineering",
}

# Alias-key fixes where two dictionary entries compete (first index wins).
KEY_OVERRIDES: dict[str, str] = {
    "postgres": "postgresql",
    "mongo": "mongodb",
    "postgre": "postgresql",
}


def _display_name(canonical_lower: str) -> str:
    if canonical_lower in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[canonical_lower]
    return " ".join(w.capitalize() for w in canonical_lower.split())


def _keys_for(token: str) -> list[str]:
    """Generate normalized lookup keys for a raw skill token."""
    t = token.lower().strip()
    # Strip version suffixes: "Python 3", "java 11", "Angular v14".
    t = re.sub(r"\s*(?:v(?:er(?:sion)?)?\.?\s*)?\d+(?:\.\d+)*$", "", t).strip()
    keys = []
    compact = re.sub(r"[^a-z0-9+#]", "", t)
    spaced = re.sub(r"\s+", " ", t)
    for candidate in (spaced, compact):
        if candidate and candidate not in keys:
            keys.append(candidate)
    return keys


def _build_index() -> tuple[dict[str, tuple[str, SkillCategory]], dict[str, tuple[str, SkillCategory]]]:
    """Build (name_index, alias_index): key -> (canonical_name, category)."""
    name_index: dict[str, tuple[str, SkillCategory]] = {}
    alias_index: dict[str, tuple[str, SkillCategory]] = {}

    def category_for(name_lower: str, db_category_key: str) -> SkillCategory:
        if name_lower in PER_NAME_CATEGORY:
            return PER_NAME_CATEGORY[name_lower]
        return CATEGORY_MAP.get(db_category_key, SkillCategory.OTHER)

    source: list[tuple[str, dict[str, object]]] = []
    for db_key, entries in SKILL_DATABASE.items():
        for entry in entries:
            source.append((db_key, entry))
    for db_key, entries in EXTRA_ENTRIES.items():
        for entry in entries:
            source.append((db_key, entry))

    for db_key, entry in source:
        name = str(entry["name"]).lower()
        category = category_for(name, db_key)
        for key in _keys_for(name):
            name_index.setdefault(key, (name, category))
        for alias in entry.get("aliases", []) or []:
            alias_l = str(alias).lower()
            for key in _keys_for(alias_l):
                alias_index.setdefault(key, (name, category))

    # Alias-key fixes: e.g. "postgres" must resolve to the PostgreSQL entry,
    # not to the generic "sql" entry that also lists it as an alias.
    resolved_alias: dict[str, tuple[str, SkillCategory]] = {}
    for key, value in alias_index.items():
        target_key = KEY_OVERRIDES.get(key)
        resolved_alias[key] = (
            name_index[target_key] if target_key and target_key in name_index else value
        )
    return name_index, resolved_alias


_NAME_INDEX, _ALIAS_INDEX = _build_index()

_FUZZY_CANDIDATES = [
    (k, v) for k, v in {**_ALIAS_INDEX, **_NAME_INDEX}.items() if len(k) >= 5
]


class SkillNormalizer:
    """Normalizes raw skill strings to canonical ``NormalizedSkill`` objects."""

    @staticmethod
    def normalize(raw: str | None) -> NormalizedSkill | None:
        if not raw or not raw.strip():
            return None
        raw_text = raw.strip()
        keys = _keys_for(raw_text)

        hit = None
        matched_on = raw_text
        for key in keys:
            if key in _NAME_INDEX:
                hit = _NAME_INDEX[key]
                break
        if hit is None:
            for key in keys:
                if key in _ALIAS_INDEX:
                    hit = _ALIAS_INDEX[key]
                    break
        if hit is None and len(raw_text) >= 5:
            compact = re.sub(r"[^a-z0-9+#]", "", raw_text.lower())
            best_ratio, best_hit = 0.0, None
            for cand_key, cand_val in _FUZZY_CANDIDATES:
                if compact[:1] != cand_key[:1]:
                    continue
                ratio = SequenceMatcher(None, compact, cand_key).ratio()
                if ratio > best_ratio:
                    best_ratio, best_hit = ratio, cand_val
            if best_hit is not None and best_ratio >= 0.93:
                hit = best_hit

        if hit is None:
            return None
        name, category = hit
        return NormalizedSkill(
            name=_display_name(name),
            category=category.value,
            matched_on=matched_on,
        )

    @staticmethod
    def normalize_list(raws: list[str] | None) -> list[NormalizedSkill]:
        seen: set[str] = set()
        out: list[NormalizedSkill] = []
        for raw in raws or []:
            skill = SkillNormalizer.normalize(raw)
            if skill and skill.name.lower() not in seen:
                seen.add(skill.name.lower())
                out.append(skill)
        return out

    @staticmethod
    def is_known_skill(raw: str | None) -> bool:
        return SkillNormalizer.normalize(raw) is not None

    @staticmethod
    def merge(
        primary: list[NormalizedSkill], extra: list[NormalizedSkill]
    ) -> list[NormalizedSkill]:
        """Merge two skill lists, dropping duplicates by canonical name."""
        seen: set[str] = set()
        out: list[NormalizedSkill] = []
        for skill in [*primary, *extra]:
            if skill.name.lower() not in seen:
                seen.add(skill.name.lower())
                out.append(skill)
        return out

    @staticmethod
    def extract_from_text(
        text: str | None, categories: set[str] | None = None
    ) -> list[NormalizedSkill]:
        """Find dictionary-known skills mentioned in free text (e.g. a JD).

        Deterministic scan over the shared skill index (longest key first,
        word-boundary aware). Unknown words never produce a skill. Results are
        de-duplicated by canonical name, preserving first occurrence order.
        """
        if not text:
            return []
        haystack = text.lower()
        found: list[NormalizedSkill] = []
        seen: set[str] = set()
        for key, (name, category) in sorted(
            {**_ALIAS_INDEX, **_NAME_INDEX}.items(), key=lambda kv: -len(kv[0])
        ):
            # Ultra-short keys ("go", "r", "c") match ordinary English words in
            # free text; only allow short keys made of tech symbols (c#, c++).
            if len(key) < 3 and not any(ch in key for ch in "#+"):
                continue
            if categories is not None and category.value not in categories:
                continue
            pattern = r"(?<![a-z0-9+#])" + re.escape(key) + r"(?![a-z0-9+#])"
            match = re.search(pattern, haystack)
            if not match:
                continue
            display = _display_name(name)
            if display.lower() in seen:
                continue
            seen.add(display.lower())
            found.append(
                NormalizedSkill(
                    name=display,
                    category=category.value,
                    matched_on=match.group(0),
                )
            )
        return found


def normalize_display(name: str) -> str:
    """Public helper: canonical display name for a known skill."""
    return _display_name(name.lower())
