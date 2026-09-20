from __future__ import annotations

import re
from typing import Any


class SkillGraph:
    """Comprehensive skill knowledge graph for semantic matching.

    Maps synonyms, transferable skills, related technologies,
    and category-level similarities for intelligent candidate-job matching.
    """

    # ─── Canonical skill → set of known aliases / synonyms ────────────
    SYNONYMS: dict[str, list[str]] = {
        # Programming Languages
        "javascript": ["js", "ecmascript", "es6", "es2015", "es2017", "es2020", "es2022", "esnext"],
        "typescript": ["ts"],
        "python": ["py", "python3", "cpython"],
        "java": ["jdk", "jvm"],
        "c#": ["csharp", "c sharp", ".net", "dotnet"],
        "c++": ["cpp", "c plus plus"],
        "c": ["ansi c", "c language"],
        "go": ["golang"],
        "rust": ["rs"],
        "ruby": ["rb"],
        "php": ["php8", "php7"],
        "swift": ["swiftui", "swift5"],
        "kotlin": ["kt", "kotlin/jvm"],
        "scala": ["sc"],
        "r": ["r language", "r programming"],
        "matlab": ["mat-lab"],
        "perl": ["pl"],
        "lua": [],
        "dart": ["flutter"],
        "elixir": ["ex"],
        "haskell": ["hs"],
        "clojure": ["clj"],
        "groovy": [],
        "julia": [],
        "zig": [],
        "nim": [],
        "sql": ["structured query language", "t-sql", "tsql", "plsql", "pl/sql"],
        "html": ["html5", "hypertext markup language"],
        "css": ["css3", "cascading style sheets", "sass", "scss", "less", "stylus", "tailwind", "tailwindcss", "tailwind css"],
        # Frontend Frameworks
        "react": ["reactjs", "react.js", "react18", "react19"],
        "react native": ["react-native", "reactnative"],
        "angular": ["angularjs", "angular2", "angular14", "angular15", "angular16", "angular17", "ng"],
        "vue": ["vuejs", "vue.js", "vue3", "vue2", "vuepress", "nuxt", "nuxtjs"],
        "svelte": ["sveltekit", "svelte js"],
        "next.js": ["nextjs", "next", "next13", "next14"],
        "ember": ["emberjs", "ember.js"],
        "backbone": ["backbonejs", "backbone.js"],
        "preact": [],
        "solidjs": ["solid"],
        "htmx": [],
        # Backend Frameworks
        "node.js": ["nodejs", "node", "node18", "node20"],
        "express": ["expressjs", "express.js", "express4", "express5"],
        "fastapi": ["fast api", "fast-api"],
        "django": ["django-rest", "drf", "django rest framework"],
        "flask": ["flask-restful", "flask-restx"],
        "spring": ["spring boot", "springboot", "spring-mvc", "spring-cloud", "spring framework"],
        "laravel": ["laravel-echo"],
        "rails": ["ruby on rails", "ror", "ruby on rails 7"],
        "asp.net": ["aspnet", "asp dot net", "asp.net core", "aspnetcore"],
        "gin": ["gin-gonic"],
        "fiber": ["gofiber"],
        "actix": ["actix-web"],
        "hono": [],
        "nestjs": ["nest.js", "nest"],
        "graphql": ["gql", "apollo", "apollo server", "apollo client", "relay"],
        "rest": ["restful", "rest api", "rest apis", "restful api", "rest apis"],
        "grpc": ["g-rpc", "protobuf", "protocol buffers"],
        "websocket": ["ws", "websockets", "socket.io"],
        # Databases
        "postgresql": ["postgres", "psql", "pg"],
        "mysql": ["mariadb", "mysql8", "mysql5"],
        "mongodb": ["mongo", "mongo db"],
        "redis": ["redis-cache", "redis stack"],
        "elasticsearch": ["elastic", "elk", "opensearch"],
        "dynamodb": ["dynamo db", "dynamo"],
        "cassandra": ["cass"],
        "couchdb": ["couch db", "couchbase"],
        "sqlite": ["lite", "sqlitedb"],
        "neo4j": [],
        "influxdb": ["influx"],
        "timescaledb": ["timescale"],
        "cockroachdb": ["crdb", "cockroach"],
        "firebase": ["fire store", "firestore"],
        "supabase": [],
        "planetscale": ["planet scale"],
        "mariadb": ["maria"],
        # Cloud
        "aws": ["amazon web services", "amazon cloud", "aws cloud"],
        "gcp": ["google cloud platform", "google cloud", "googlecloud"],
        "azure": ["microsoft azure", "azure cloud"],
        "cloudflare": ["cf workers", "cloudflare workers"],
        "digitalocean": ["digital ocean", "do"],
        "heroku": [],
        "vercel": ["zeit", "vercel edge"],
        "netlify": [],
        "linode": [],
        "vultr": [],
        # DevOps / Infrastructure
        "docker": ["docker-compose", "dockerfile", "docker desktop", "containerization", "containers"],
        "kubernetes": ["k8s", "kubeadm", "helm", "kustomize"],
        "terraform": ["tf", "infrastructure as code", "iac", "hcl"],
        "ansible": ["playbook", "ansible-playbook"],
        "jenkins": ["ci/cd pipeline", "jenkins pipeline"],
        "github actions": ["gha", "github ci"],
        "gitlab ci": ["gitlab-ci", "gitlab-ci/cd"],
        "circleci": ["circle ci", "circle ci/cd"],
        "travis": ["travis ci"],
        "ci/cd": ["ci cd", "continuous integration", "continuous deployment", "continuous delivery", "pipeline"],
        "nginx": ["nginx-ingress", "reverse proxy"],
        "apache": ["apache httpd", "httpd", "apache2"],
        "haproxy": ["ha proxy"],
        "istio": ["service mesh"],
        "prometheus": ["prom"],
        "grafana": [],
        "datadog": ["dd"],
        "new relic": ["newrelic"],
        "aws cloudwatch": ["cloudwatch"],
        # AI / ML
        "machine learning": ["ml", "statistical learning"],
        "deep learning": ["dl", "neural networks", "neural nets"],
        "natural language processing": ["nlp", "text processing"],
        "computer vision": ["cv", "image processing"],
        "tensorflow": ["tf", "keras", "tf.keras"],
        "pytorch": ["torch", "py-torch"],
        "scikit-learn": ["sklearn", "scikit learn"],
        "pandas": ["pd"],
        "numpy": ["np"],
        "scipy": [],
        "keras": ["tf.keras"],
        "hugging face": ["huggingface", "hf", "transformers"],
        "langchain": ["lang chain"],
        "openai": ["gpt", "gpt-4", "gpt-3.5", "chatgpt", "llm", "llms"],
        "llamaindex": ["llama index"],
        "spacy": ["spacy-nlp"],
        "nltk": [],
        "opencv": ["cv2"],
        "xgboost": ["xgb"],
        "lightgbm": ["lgbm"],
        "catboost": [],
        "neural networks": ["ann", "cnn", "rnn", "lstm", "gan", "transformer"],
        "mlops": ["machine learning operations", "ml ops"],
        "mlflow": ["ml flow"],
        "airflow": ["apache airflow"],
        "dbt": ["data build tool"],
        # Data
        "spark": ["apache spark", "pyspark", "spark sql", "spark streaming"],
        "hadoop": ["hdfs", "mapreduce", "hive"],
        "kafka": ["apache kafka", "kafka streams"],
        "snowflake": [],
        "bigquery": ["big query", "bq"],
        "redshift": ["aws redshift"],
        "etl": ["extract transform load", "data pipeline"],
        "data warehousing": ["dw", "data warehouse"],
        "data lake": ["data lakehouse", "lakehouse"],
        "tableau": [],
        "power bi": ["powerbi", "pbi"],
        "looker": [],
        "metabase": [],
        "superset": ["apache superset"],
        # Mobile
        "ios": ["iphone", "ipad", "apple", "swiftui", "uikit"],
        "android": ["android development", "kotlin android", "java android"],
        "flutter": ["dart"],
        "react native": ["react-native", "rn"],
        "xamarin": [],
        "ionic": [],
        "capacitor": [],
        # Testing
        "jest": ["javascript testing"],
        "pytest": ["py test"],
        "cypress": ["e2e testing", "end to end testing"],
        "playwright": [],
        "selenium": ["selenium web driver", "webdriver"],
        "mocha": [],
        "chai": [],
        "junit": ["junit5", "junit 5"],
        "testng": ["test ng"],
        "rspec": ["ruby testing"],
        "xctest": [],
        "k6": ["load testing"],
        "jmeter": ["apache jmeter"],
        "postman": ["api testing"],
        # Security
        "owasp": ["owasp top 10", "application security"],
        "penetration testing": ["pentest", "pen testing"],
        "oauth": ["oauth2", "oauth 2.0"],
        "jwt": ["json web token", "json web tokens"],
        "saml": ["sso"],
        "ssl": ["tls", "https", "certificates"],
        "vault": ["hashicorp vault", "secrets management"],
        "sonarqube": ["sonar cloud", "code quality"],
        "snyk": ["vulnerability scanning"],
        # Soft Skills
        "leadership": ["team lead", "tech lead", "technical lead", "engineering manager"],
        "communication": ["verbal communication", "written communication"],
        "teamwork": ["collaboration", "team player"],
        "problem solving": ["analytical thinking", "critical thinking", "troubleshooting"],
        "agile": ["scrum", "kanban", "sprint", "agile methodology", "agile/scrum"],
        "mentoring": ["coaching", "training", "teaching"],
        "project management": ["pm", "product management", "scrum master"],
        "time management": [],
        "adaptability": [],
        "creativity": ["innovation", "creative thinking"],
        # Domain / Industry
        "fintech": ["financial technology", "finance tech"],
        "healthtech": ["health tech", "healthcare technology", "medtech"],
        "edtech": ["education technology", "ed-tech"],
        "e-commerce": ["ecommerce", "retail tech"],
        "saas": ["software as a service", "b2b saas"],
        "microservices": ["micro-service", "microservice architecture", "distributed systems"],
        "event driven": ["event-driven", "event sourcing", "cqrs"],
        "serverless": ["faas", "function as a service", "lambda", "aws lambda"],
        "web3": ["blockchain", "web 3", "defi", "smart contracts"],
        "cybersecurity": ["information security", "infosec", "network security"],
        # Version Control
        "git": ["github", "gitlab", "bitbucket", "version control", "vcs"],
        "svn": ["subversion"],
        # Office / Productivity
        "jira": ["atlassian jira", "project tracking"],
        "confluence": ["atlassian confluence"],
        "notion": [],
        "slack": [],
        "teams": ["microsoft teams"],
        "figma": ["ui/ux design", "design tool"],
        "sketch": [],
        "adobe xd": [],
    }

    # ─── Transferable skill groups ────────────────────────────────────
    # Skills in the same group can partially substitute each other.
    TRANSFERABLE_GROUPS: dict[str, list[str]] = {
        "frontend_frameworks": [
            "react", "angular", "vue", "svelte", "preact", "solidjs", "backbone", "ember",
        ],
        "backend_frameworks_python": ["fastapi", "django", "flask", "sanic", "starlette"],
        "backend_frameworks_js": ["express", "nestjs", "koa", "hapi", "fastify", "hono"],
        "backend_frameworks_java": ["spring", "quarkus", "micronaut"],
        "backend_frameworks_go": ["gin", "fiber", "echo", "chi", "mux"],
        "relational_databases": [
            "postgresql", "mysql", "sqlite", "mariadb", "cockroachdb", "oracle", "sql server",
        ],
        "nosql_databases": [
            "mongodb", "dynamodb", "cassandra", "couchdb", "neo4j", "redis",
        ],
        "cloud_providers": ["aws", "gcp", "azure"],
        "container_orchestration": ["kubernetes", "docker swarm", "nomad", "ecs", "fargate"],
        "ci_cd_tools": [
            "jenkins", "github actions", "gitlab ci", "circleci", "travis",
        ],
        "monitoring_tools": ["prometheus", "grafana", "datadog", "new relic", "splunk"],
        "ml_frameworks": ["tensorflow", "pytorch", "scikit-learn", "keras", "xgboost", "lightgbm"],
        "data_processing": ["spark", "hadoop", "kafka", "flink", "storm"],
        "mobile_frameworks": ["flutter", "react native", "xamarin", "ionic"],
        "testing_frameworks": ["jest", "pytest", "mocha", "junit", "xctest"],
        "message_brokers": ["kafka", "rabbitmq", "activemq", "nats", "pulsar"],
        "api_styles": ["rest", "graphql", "grpc", "websocket"],
        "infrastructure_as_code": ["terraform", "pulumi", "cloudformation", "ansible"],
        "css_frameworks": ["tailwind", "bootstrap", "bulma", "material-ui", "chakra"],
        "state_management": ["redux", "zustand", "mobx", "recoil", "jotai", "vuex", "pinia"],
        "job_queues": ["celery", "bull", "sidekiq", "rq", "dramatiq"],
        "search_engines": ["elasticsearch", "opensearch", "meilisearch", "typesense", "algolia"],
    }

    # ─── Skill similarity scores (pair → float 0–1) ──────────────────
    # For skills not explicitly listed, a default score is used.
    PAIRWISE_SIMILARITY: dict[tuple[str, str], float] = {
        ("react", "angular"): 0.75,
        ("react", "vue"): 0.75,
        ("react", "svelte"): 0.70,
        ("angular", "vue"): 0.75,
        ("node.js", "deno"): 0.80,
        ("python", "r"): 0.60,
        ("java", "kotlin"): 0.85,
        ("java", "scala"): 0.70,
        ("c#", "java"): 0.75,
        ("c#", "f#"): 0.80,
        ("c++", "rust"): 0.65,
        ("go", "rust"): 0.70,
        ("postgresql", "mysql"): 0.85,
        ("mongodb", "couchdb"): 0.70,
        ("aws", "gcp"): 0.80,
        ("aws", "azure"): 0.80,
        ("gcp", "azure"): 0.80,
        ("docker", "podman"): 0.85,
        ("kubernetes", "docker swarm"): 0.65,
        ("terraform", "pulumi"): 0.80,
        ("terraform", "ansible"): 0.50,
        ("jenkins", "github actions"): 0.70,
        ("tensorflow", "pytorch"): 0.80,
        ("spark", "hadoop"): 0.60,
        ("kafka", "rabbitmq"): 0.65,
        ("elasticsearch", "opensearch"): 0.90,
        ("redux", "zustand"): 0.70,
        ("jest", "mocha"): 0.70,
        ("jest", "pytest"): 0.50,
        ("flask", "django"): 0.70,
        ("fastapi", "flask"): 0.70,
        ("fastapi", "django"): 0.65,
        ("express", "nestjs"): 0.75,
        ("spring", "quarkus"): 0.75,
        ("tailwind", "bootstrap"): 0.60,
        ("graphql", "rest"): 0.55,
        ("redis", "memcached"): 0.65,
        ("airflow", "prefect"): 0.75,
        ("airflow", "dagster"): 0.75,
        ("mlflow", "wandb"): 0.70,
        ("tableau", "power bi"): 0.80,
        ("snowflake", "bigquery"): 0.75,
        ("postgres", "mysql"): 0.85,
    }

    DEFAULT_SIMILARITY = 0.40
    DEFAULT_TRANSFERABLE_BONUS = 0.15

    # ─── Public API ───────────────────────────────────────────────────

    @classmethod
    def normalize(cls, skill: str) -> str:
        return re.sub(r"[\s\-_]+", " ", skill.lower().strip())

    @classmethod
    def find_canonical(cls, skill: str) -> str | None:
        """Return the canonical form if skill is a known alias."""
        normalized = cls.normalize(skill)
        for canonical, aliases in cls.SYNONYMS.items():
            if normalized == cls.normalize(canonical):
                return canonical
            for alias in aliases:
                if normalized == cls.normalize(alias):
                    return canonical
        return None

    @classmethod
    def are_synonyms(cls, skill_a: str, skill_b: str) -> bool:
        """Check if two skills are synonyms (direct match or alias match)."""
        a = cls.normalize(skill_a)
        b = cls.normalize(skill_b)
        if a == b:
            return True
        can_a = cls.find_canonical(skill_a)
        can_b = cls.find_canonical(skill_b)
        if can_a and can_b and can_a == can_b:
            return True
        if can_a:
            aliases = [cls.normalize(x) for x in cls.SYNONYMS.get(can_a, [])]
            if b in aliases or b == cls.normalize(can_a):
                return True
        if can_b:
            aliases = [cls.normalize(x) for x in cls.SYNONYMS.get(can_b, [])]
            if a in aliases or a == cls.normalize(can_b):
                return True
        return False

    @classmethod
    def similarity_score(cls, skill_a: str, skill_b: str) -> float:
        """Return a similarity score 0.0–1.0 between two skills."""
        a = cls.normalize(skill_a)
        b = cls.normalize(skill_b)
        if a == b:
            return 1.0
        can_a = cls.find_canonical(skill_a)
        can_b = cls.find_canonical(skill_b)
        if can_a and can_b:
            if can_a == can_b:
                return 1.0
            pair = tuple(sorted([can_a, can_b]))
            if pair in cls.PAIRWISE_SIMILARITY:
                return cls.PAIRWISE_SIMILARITY[pair]
        for group_skills in cls.TRANSFERABLE_GROUPS.values():
            normalized_group = [cls.normalize(s) for s in group_skills]
            if a in normalized_group and b in normalized_group:
                return 0.65
        if a in b or b in a:
            return 0.70
        return cls.DEFAULT_SIMILARITY

    @classmethod
    def is_transferable(cls, skill_a: str, skill_b: str) -> bool:
        """Check if two skills belong to the same transferable group."""
        a = cls.normalize(skill_a)
        b = cls.normalize(skill_b)
        for group_skills in cls.TRANSFERABLE_GROUPS.values():
            normalized_group = [cls.normalize(s) for s in group_skills]
            if a in normalized_group and b in normalized_group:
                return True
        return False

    @classmethod
    def get_related_skills(cls, skill: str) -> list[str]:
        """Return all skills related to the given skill."""
        normalized = cls.normalize(skill)
        related: list[str] = []
        for group_skills in cls.TRANSFERABLE_GROUPS.values():
            normalized_group = [cls.normalize(s) for s in group_skills]
            if normalized in normalized_group:
                for s in group_skills:
                    if cls.normalize(s) != normalized:
                        related.append(s)
                break
        can = cls.find_canonical(skill)
        if can:
            for pair, score in cls.PAIRWISE_SIMILARITY.items():
                if can in pair and score >= 0.60:
                    other = pair[0] if pair[1] == can else pair[1]
                    if other not in related:
                        related.append(other)
        return related

    @classmethod
    def extract_skills_from_text(cls, text: str) -> list[str]:
        """Extract known skills from free-form text."""
        text_lower = text.lower()
        found: list[str] = []
        all_known: dict[str, str] = {}
        for canonical, aliases in cls.SYNONYMS.items():
            all_known[cls.normalize(canonical)] = canonical
            for alias in aliases:
                all_known[cls.normalize(alias)] = canonical
        for normalized, canonical in sorted(all_known.items(), key=lambda x: -len(x[0])):
            pattern = r'\b' + re.escape(normalized).replace(r'\ ', r'[\s\-_]+') + r'\b'
            if re.search(pattern, text_lower):
                if canonical not in found:
                    found.append(canonical)
        return found

    @classmethod
    def parse_search_query(cls, query: str) -> dict[str, Any]:
        """Parse a natural language search query into structured components."""
        result: dict[str, Any] = {
            "skills": [],
            "experience_years": None,
            "education": None,
            "location": None,
            "employment_type": None,
            "free_text": query,
        }
        query_lower = query.lower()
        import re as re_mod
        year_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)?',
            r'(\d+)\+?\s*yr',
            r'(\d+)\+?\s*yoe',
            r'experience:\s*(\d+)',
        ]
        for pat in year_patterns:
            m = re_mod.search(pat, query_lower)
            if m:
                result["experience_years"] = int(m.group(1))
                break
        edu_keywords = {
            "phd": "PhD", "doctorate": "PhD", "doctoral": "PhD",
            "masters": "Master", "master": "Master", "m.sc": "Master",
            "m.tech": "Master", "mba": "Master", "ms": "Master",
            "bachelors": "Bachelor", "bachelor": "Bachelor", "b.sc": "Bachelor",
            "b.tech": "Bachelor", "bs": "Bachelor", "be": "Bachelor",
            "degree": "Bachelor",
        }
        for keyword, level in edu_keywords.items():
            if keyword in query_lower:
                result["education"] = level
                break
        location_patterns = [
            r'(?:in|at|from|based in|located in)\s+([a-zA-Z\s]+?)(?:\s*,|\s+with|\s+and|\s+for|\s*$)',
            r'(?:remote|onsite|on-site|hybrid)',
        ]
        for pat in location_patterns:
            m = re_mod.search(pat, query_lower)
            if m:
                loc = m.group(0).strip()
                if loc in ("remote", "onsite", "on-site", "hybrid"):
                    result["location"] = loc
                elif len(m.groups()) > 0 and m.group(1):
                    result["location"] = m.group(1).strip()
                break
        emp_patterns = {
            r'\bfull[-\s]?time\b': "full_time",
            r'\bpart[-\s]?time\b': "part_time",
            r'\bcontract\b': "contract",
            r'\bintern(?:ship)?\b': "internship",
            r'\bfreelance\b': "freelance",
        }
        for pat, emp_type in emp_patterns.items():
            if re_mod.search(pat, query_lower):
                result["employment_type"] = emp_type
                break
        found_skills = cls.extract_skills_from_text(query)
        result["skills"] = found_skills
        return result
