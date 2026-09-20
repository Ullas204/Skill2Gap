"""Phase 9: Consolidated Learning Resource Dataset.

Single source of truth for curated learning resources. The catalog below was
moved verbatim from ``training/time_to_ready.py`` so both the Time-to-Ready
engine and the new public Learning Resource Intelligence agent read one
dataset — nothing is duplicated.

Data-integrity rules:
- URLs, durations, costs, providers and skill coverage come only from the
  pre-existing curated catalog. No new prices, durations or links are invented.
- ``verified`` is derived (never hand-set) from the shared
  ``VERIFIED_RESOURCE_HOSTS`` set used by the Training Agent: a resource is
  verified only when its link host belongs to that audited set.
- ``last_verified_at`` is always ``None`` because this dataset records no
  verification timestamp. Null is honest — an unknown date is never fabricated.
- ``description`` is assembled only from already-known real fields.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.skill2job.training.agent import VERIFIED_RESOURCE_HOSTS

RESOURCE_DATA_VERSION = "skill2job-resource-data-1.0.0"

_RESOURCE_CATALOG_RAW = [
    {"resource_id": "res_python_official", "title": "Python Official Tutorial", "provider": "python.org", "url": "https://docs.python.org/3/tutorial/", "skills": ["Python"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": [], "source_type": "official_docs", "skill_coverage": 0.8},
    {"resource_id": "res_postgresql_docs", "title": "PostgreSQL Documentation", "provider": "PostgreSQL", "url": "https://www.postgresql.org/docs/", "skills": ["SQL", "PostgreSQL"], "duration_hours": 30, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": [], "source_type": "official_docs", "skill_coverage": 0.7},
    {"resource_id": "res_mysql_docs", "title": "MySQL Reference Manual", "provider": "MySQL", "url": "https://dev.mysql.com/doc/", "skills": ["MySQL", "SQL"], "duration_hours": 25, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": [], "source_type": "official_docs", "skill_coverage": 0.7},
    {"resource_id": "res_nptel_statistics", "title": "NPTEL - Introduction to Probability and Statistics", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/111107050", "skills": ["Statistics", "Probability"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": ["Python"], "source_type": "course_catalog", "skill_coverage": 0.85},
    {"resource_id": "res_coursera_ml", "title": "Machine Learning by Andrew Ng", "provider": "Coursera / Stanford", "url": "https://www.coursera.org/learn/machine-learning", "skills": ["Machine Learning", "Linear Regression", "Neural Networks"], "duration_hours": 60, "cost": 2999, "currency": "INR", "is_free": False, "pricing_type": "subscription", "difficulty": "intermediate", "format": "self_paced", "certificate": True, "skill_level": "intermediate", "prerequisites": ["Python", "Statistics", "Linear Algebra"], "source_type": "course_catalog", "skill_coverage": 0.9},
    {"resource_id": "res_ml_free_nptel", "title": "NPTEL - Machine Learning", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102066", "skills": ["Machine Learning"], "duration_hours": 50, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": True, "skill_level": "intermediate", "prerequisites": ["Python", "Statistics"], "source_type": "course_catalog", "skill_coverage": 0.8},
    {"resource_id": "res_sklearn_docs", "title": "scikit-learn User Guide and Tutorials", "provider": "scikit-learn", "url": "https://scikit-learn.org/stable/tutorial/index.html", "skills": ["Scikit-learn", "Machine Learning"], "duration_hours": 25, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": False, "skill_level": "intermediate", "prerequisites": ["Python", "Statistics", "Machine Learning"], "source_type": "official_docs", "skill_coverage": 0.75},
    {"resource_id": "res_sklearn_metrics", "title": "scikit-learn Model Evaluation Guide", "provider": "scikit-learn", "url": "https://scikit-learn.org/stable/modules/model_evaluation.html", "skills": ["Model Evaluation", "Cross-Validation"], "duration_hours": 15, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": False, "skill_level": "intermediate", "prerequisites": ["Python", "Machine Learning"], "source_type": "official_docs", "skill_coverage": 0.8},
    {"resource_id": "res_numpy_docs", "title": "NumPy User Guide", "provider": "NumPy", "url": "https://numpy.org/doc/stable/user/index.html", "skills": ["NumPy", "Python"], "duration_hours": 20, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": ["Python"], "source_type": "official_docs", "skill_coverage": 0.7},
    {"resource_id": "res_pandas_docs", "title": "Pandas Getting Started Tutorials", "provider": "Pandas", "url": "https://pandas.pydata.org/docs/getting_started/index.html", "skills": ["Pandas", "Python"], "duration_hours": 20, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": ["Python", "NumPy"], "source_type": "official_docs", "skill_coverage": 0.7},
    {"resource_id": "res_docker_getstarted", "title": "Docker Get Started", "provider": "Docker", "url": "https://docs.docker.com/get-started/", "skills": ["Docker", "Containers"], "duration_hours": 20, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": ["Linux"], "source_type": "official_docs", "skill_coverage": 0.8},
    {"resource_id": "res_k8s_tutorials", "title": "Kubernetes Tutorials", "provider": "Kubernetes", "url": "https://kubernetes.io/docs/tutorials/", "skills": ["Kubernetes", "Containers", "Docker"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": False, "skill_level": "intermediate", "prerequisites": ["Docker", "Linux"], "source_type": "official_docs", "skill_coverage": 0.85},
    {"resource_id": "res_aws_training", "title": "AWS Cloud Practitioner Essentials", "provider": "AWS", "url": "https://aws.amazon.com/training/", "skills": ["AWS", "Cloud Computing"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": [], "source_type": "official_docs", "skill_coverage": 0.7},
    {"resource_id": "res_react_learn", "title": "React Learn", "provider": "React", "url": "https://react.dev/learn", "skills": ["React", "JavaScript", "Frontend"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": ["JavaScript", "HTML", "CSS"], "source_type": "official_docs", "skill_coverage": 0.8},
    {"resource_id": "res_fastapi_tutorial", "title": "FastAPI Tutorial", "provider": "FastAPI", "url": "https://fastapi.tiangolo.com/tutorial/", "skills": ["FastAPI", "Python", "REST API"], "duration_hours": 25, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": False, "skill_level": "intermediate", "prerequisites": ["Python"], "source_type": "official_docs", "skill_coverage": 0.85},
    {"resource_id": "res_tensorflow_tutorials", "title": "TensorFlow Tutorials", "provider": "Google / TensorFlow", "url": "https://www.tensorflow.org/tutorials", "skills": ["TensorFlow", "Deep Learning", "Machine Learning"], "duration_hours": 60, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "advanced", "format": "self_paced", "certificate": False, "skill_level": "advanced", "prerequisites": ["Python", "Machine Learning", "NumPy"], "source_type": "official_docs", "skill_coverage": 0.85},
    {"resource_id": "res_pytorch_tutorials", "title": "PyTorch Tutorials", "provider": "PyTorch", "url": "https://pytorch.org/tutorials/", "skills": ["PyTorch", "Deep Learning", "Machine Learning"], "duration_hours": 50, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "advanced", "format": "self_paced", "certificate": False, "skill_level": "advanced", "prerequisites": ["Python", "Machine Learning"], "source_type": "official_docs", "skill_coverage": 0.85},
    {"resource_id": "res_terraform_tutorials", "title": "Terraform Tutorials", "provider": "HashiCorp", "url": "https://developer.hashicorp.com/terraform/tutorials", "skills": ["Terraform", "IaC", "Cloud Computing"], "duration_hours": 30, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": False, "skill_level": "intermediate", "prerequisites": ["Cloud Computing"], "source_type": "official_docs", "skill_coverage": 0.8},
    {"resource_id": "res_kafka_docs", "title": "Apache Kafka Documentation", "provider": "Apache Kafka", "url": "https://kafka.apache.org/documentation/", "skills": ["Apache Kafka", "Message Queue"], "duration_hours": 30, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": False, "skill_level": "intermediate", "prerequisites": ["Java"], "source_type": "official_docs", "skill_coverage": 0.7},
    {"resource_id": "res_airflow_docs", "title": "Apache Airflow Documentation", "provider": "Apache Airflow", "url": "https://airflow.apache.org/docs/", "skills": ["Apache Airflow", "Data Engineering"], "duration_hours": 30, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": False, "skill_level": "intermediate", "prerequisites": ["Python"], "source_type": "official_docs", "skill_coverage": 0.75},
    {"resource_id": "res_spark_docs", "title": "Apache Spark Documentation", "provider": "Apache Spark", "url": "https://spark.apache.org/docs/latest/", "skills": ["Apache Spark", "Big Data"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "advanced", "format": "self_paced", "certificate": False, "skill_level": "advanced", "prerequisites": ["Python", "SQL"], "source_type": "official_docs", "skill_coverage": 0.75},
    {"resource_id": "res_django_tutorial", "title": "Django Tutorial", "provider": "Django", "url": "https://docs.djangoproject.com/en/stable/intro/tutorial01/", "skills": ["Django", "Python", "Backend"], "duration_hours": 35, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": ["Python", "HTML"], "source_type": "official_docs", "skill_coverage": 0.8},
    {"resource_id": "res_nodejs_guide", "title": "Node.js Guide", "provider": "Node.js", "url": "https://nodejs.org/en/learn", "skills": ["Node.js", "JavaScript", "Backend"], "duration_hours": 30, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": False, "skill_level": "beginner", "prerequisites": ["JavaScript"], "source_type": "official_docs", "skill_coverage": 0.75},
    {"resource_id": "res_mongodb_university", "title": "MongoDB University", "provider": "MongoDB", "url": "https://learn.mongodb.com/", "skills": ["MongoDB", "NoSQL", "Database"], "duration_hours": 30, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": [], "source_type": "official_docs", "skill_coverage": 0.8},
    {"resource_id": "res_skill_india", "title": "Skill India Digital Hub", "provider": "Skill India", "url": "https://www.skillindiadigital.gov.in/", "skills": [], "duration_hours": None, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "unknown", "format": "unknown", "certificate": True, "skill_level": "unknown", "prerequisites": [], "source_type": "course_catalog", "skill_coverage": 0.3},
    {"resource_id": "res_nptel_python", "title": "NPTEL - Programming in Python (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102066", "skills": ["Python"], "duration_hours": 35, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": [], "source_type": "course_catalog", "skill_coverage": 0.75},
    {"resource_id": "res_nptel_dbms", "title": "NPTEL - Database Management Systems (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106105153", "skills": ["SQL", "Database Management"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": [], "source_type": "course_catalog", "skill_coverage": 0.8},
    {"resource_id": "res_nptel_java", "title": "NPTEL - Programming in Java (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102052", "skills": ["Java"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": [], "source_type": "course_catalog", "skill_coverage": 0.8},
    {"resource_id": "res_nptel_linux", "title": "NPTEL - Unix Programming (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102054", "skills": ["Linux", "Unix"], "duration_hours": 30, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": [], "source_type": "course_catalog", "skill_coverage": 0.75},
    {"resource_id": "res_nptel_cloud", "title": "NPTEL - Cloud Computing (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102115", "skills": ["Cloud Computing", "AWS"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": True, "skill_level": "intermediate", "prerequisites": ["Linux"], "source_type": "course_catalog", "skill_coverage": 0.7},
    {"resource_id": "res_nptel_bigs", "title": "NPTEL - Big Data Computing (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102149", "skills": ["Apache Spark", "Big Data"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "advanced", "format": "self_paced", "certificate": True, "skill_level": "advanced", "prerequisites": ["Python", "SQL"], "source_type": "course_catalog", "skill_coverage": 0.7},
    {"resource_id": "res_nptel_security", "title": "NPTEL - Information Security (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102084", "skills": ["Security", "Cryptography"], "duration_hours": 40, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": True, "skill_level": "intermediate", "prerequisites": ["Linux"], "source_type": "course_catalog", "skill_coverage": 0.75},
    {"resource_id": "res_nptel_data_analytics", "title": "NPTEL - Data Analytics with Python (IIT Roorkee)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106105147", "skills": ["Data Analysis", "Python", "Pandas"], "duration_hours": 35, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": True, "skill_level": "intermediate", "prerequisites": ["Python"], "source_type": "course_catalog", "skill_coverage": 0.8},
    {"resource_id": "res_nptel_scala", "title": "NPTEL - Programming in Scala (IIT Bombay)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102180", "skills": ["Scala"], "duration_hours": 35, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "intermediate", "format": "self_paced", "certificate": True, "skill_level": "intermediate", "prerequisites": [], "source_type": "course_catalog", "skill_coverage": 0.7},
    {"resource_id": "res_nptel_ml", "title": "NPTEL - Deep Learning (IIT Kharagpur)", "provider": "NPTEL", "url": "https://nptel.ac.in/courses/106102126", "skills": ["Deep Learning", "Machine Learning"], "duration_hours": 45, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "advanced", "format": "self_paced", "certificate": True, "skill_level": "advanced", "prerequisites": ["Python", "Machine Learning"], "source_type": "course_catalog", "skill_coverage": 0.8},
    {"resource_id": "res_skill_india_hub", "title": "Skill India Digital Hub - Technology Courses", "provider": "Skill India", "url": "https://www.skillindiadigital.gov.in/", "skills": ["Web Development", "Digital Literacy"], "duration_hours": 20, "cost": 0, "currency": "INR", "is_free": True, "pricing_type": "free", "difficulty": "beginner", "format": "self_paced", "certificate": True, "skill_level": "beginner", "prerequisites": [], "source_type": "course_catalog", "skill_coverage": 0.5},
]


def _host_verified(resource: dict) -> bool:
    """A resource is verified only when its link host is in the audited set."""
    url = resource.get("url") or ""
    return bool(urlparse(url).netloc in VERIFIED_RESOURCE_HOSTS)


def _describe(resource: dict) -> str:
    """Deterministic description assembled only from existing real fields."""
    cost_label = "free" if resource.get("is_free") else (
        "paid" if (resource.get("cost") or 0) > 0 else "cost-unknown"
    )
    parts = [cost_label]
    fmt = (resource.get("format") or "unknown").replace("_", " ")
    if fmt and fmt != "unknown":
        parts.append(fmt)
    difficulty = (resource.get("difficulty") or "unknown").replace("_", " ")
    if difficulty and difficulty != "unknown":
        parts.append(difficulty)
    skills = list(resource.get("skills") or [])
    description = f"{' '.join(parts)} learning resource by {resource.get('provider')}."
    if skills:
        description += f" Covers: {', '.join(skills[:5])}."
    else:
        description += " No specific skills listed."
    return description


def _build_catalog() -> list[dict]:
    enriched: list[dict] = []
    for resource in _RESOURCE_CATALOG_RAW:
        entry = dict(resource)
        entry["verified"] = _host_verified(resource)
        entry["last_verified_at"] = None
        entry["description"] = _describe(resource)
        enriched.append(entry)
    return enriched


_RESOURCE_CATALOG = _build_catalog()


def sort_key(resource: dict, mode: str = "balanced") -> tuple:
    """Deterministic, mode-aware ranking key for resource selection.

    - balanced  → current behaviour (free first, then coverage, then duration)
    - cheapest  → ascending cost (unknown cost ranks last, never treated as 0)
    - fastest   → ascending duration (unknown duration ranks last)
    - free_only → free resources first, then balanced
    """
    is_free = resource.get("is_free", False)
    coverage = resource.get("skill_coverage") or 0.0
    duration = resource.get("duration_hours")
    cost = resource.get("cost")
    if mode == "fastest":
        return (
            duration if duration is not None else 999.0,
            0 if is_free else 1,
            -coverage,
        )
    if mode == "cheapest":
        return (
            cost if cost is not None else float("inf"),
            0 if is_free else 1,
            -coverage,
        )
    free_rank = 0 if is_free else 1
    if mode == "free_only":
        if not is_free:
            return (1, 0, 0)
        return (0, free_rank, -coverage)
    return (free_rank, -coverage, duration if duration is not None else 999.0)