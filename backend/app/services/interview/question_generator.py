"""AI Interview Question Generator.

Rule-based + template-driven question generation engine.
Extracts skills and requirements from job descriptions and candidate profiles
to produce relevant, personalized interview questions.
"""

from __future__ import annotations

import random
import re


class QuestionGenerator:
    # ─── Skill → Question Mapping ─────────────────────────────────

    _SKILL_QUESTIONS: dict[str, dict[str, list[str]]] = {
        "python": {
            "technical": [
                "Explain the difference between a list and a tuple in Python. When would you use each?",
                "What are decorators in Python and how would you use them in a real project?",
                "Explain Python's GIL (Global Interpreter Lock). How does it affect concurrency?",
                "How does memory management work in Python? Describe the reference counting mechanism.",
                "What are metaclasses in Python and when would you use them?",
                "Explain the difference between __new__ and __init__ in Python.",
                "What are generators and how do they differ from regular functions?",
                "Describe the difference between deep copy and shallow copy in Python.",
                "How would you handle exceptions in a Python application? Describe best practices.",
                "Explain list comprehensions vs generator expressions. When would you prefer one over the other?",
            ],
            "coding": [
                "Write a function to find the second largest number in a list without using built-in sorting.",
                "Implement a LRU cache from scratch in Python.",
                "Write a function that flattens a nested list of arbitrary depth.",
                "Implement a context manager for database connection handling.",
                "Write a decorator that retries a function call up to N times on exception.",
            ],
        },
        "javascript": {
            "technical": [
                "Explain the event loop in JavaScript. How does it handle asynchronous operations?",
                "What is the difference between var, let, and const in JavaScript?",
                "Describe closures in JavaScript with a practical example.",
                "What are Promises and how do they differ from callbacks?",
                "Explain the difference between == and === in JavaScript.",
                "What is prototypal inheritance? How does it differ from classical inheritance?",
                "How does the 'this' keyword work in different contexts?",
                "Explain ES6 modules and how they differ from CommonJS modules.",
                "What are WeakMaps and WeakSets? When would you use them?",
                "Describe the difference between synchronous and asynchronous code execution.",
            ],
            "coding": [
                "Implement a debounce function in JavaScript.",
                "Write a function to deep clone a nested object without using JSON.parse/stringify.",
                "Implement a simple EventEmitter class in JavaScript.",
                "Write a function to flatten a nested object with dot notation keys.",
                "Implement Promise.all() from scratch.",
            ],
        },
        "react": {
            "technical": [
                "Explain the React component lifecycle. What are the main phases?",
                "What is the Virtual DOM and how does React use it for performance?",
                "Describe the difference between state and props in React.",
                "What are React hooks? Explain useState and useEffect with examples.",
                "How does React handle list rendering and why are keys important?",
                "Explain React.memo and when you should use it for optimization.",
                "What is the Context API and when would you use it vs Redux?",
                "Describe React's reconciliation algorithm.",
                "What are controlled vs uncontrolled components?",
                "How would you handle error boundaries in a React application?",
            ],
            "coding": [
                "Build a custom useLocalStorage hook in React.",
                "Implement a virtualized list component that handles 10,000+ items.",
                "Create a useDebounce custom hook.",
                "Write a React component that implements infinite scrolling.",
                "Build a useFetch hook with caching, retry, and abort controller support.",
            ],
        },
        "fastapi": {
            "technical": [
                "Explain how FastAPI handles dependency injection. Provide an example.",
                "What is the difference between async and sync endpoint functions in FastAPI?",
                "How does FastAPI's Pydantic validation work?",
                "Describe how to implement authentication in a FastAPI application.",
                "What are middleware in FastAPI and how do you create custom middleware?",
                "Explain FastAPI's background tasks feature.",
                "How do you handle file uploads in FastAPI?",
                "Describe how to implement rate limiting in FastAPI.",
                "What is the difference between APIRouter and FastAPI app instances?",
                "How would you structure a large FastAPI application?",
            ],
            "coding": [
                "Create a FastAPI endpoint that validates a complex nested Pydantic model.",
                "Implement a FastAPI middleware that logs all requests and response times.",
                "Write a FastAPI WebSocket endpoint for real-time notifications.",
                "Implement a pagination system for a FastAPI list endpoint.",
                "Create a FastAPI background task that processes uploaded files.",
            ],
        },
        "sql": {
            "technical": [
                "Explain the difference between INNER JOIN, LEFT JOIN, RIGHT JOIN, and FULL JOIN.",
                "What are database indexes and when should you use them?",
                "Describe the ACID properties of a database transaction.",
                "What is the difference between WHERE and HAVING clauses?",
                "Explain normalization and when you might denormalize a database.",
                "What are stored procedures and when would you use them?",
                "How does query optimization work? Describe EXPLAIN plans.",
                "What are common table expressions (CTEs) and when would you use them?",
                "Describe the difference between optimistic and pessimistic locking strategies.",
                "What are window functions in SQL? Provide examples.",
            ],
            "coding": [
                "Write a SQL query to find the second highest salary from an employees table.",
                "Write a query to find duplicate records in a table.",
                "Write a query to calculate running totals.",
                "Write a query to find employees who earn more than their managers.",
                "Write a query to pivot rows into columns.",
            ],
        },
        "java": {
            "technical": [
                "Explain the JVM architecture and how Java achieves platform independence.",
                "What are the principles of OOP? How does Java implement each?",
                "Describe the difference between an interface and an abstract class.",
                "What is the Java Collections Framework? Explain HashMap internals.",
                "How does garbage collection work in Java?",
                "Explain the difference between synchronized and volatile.",
                "What are generics in Java and how do they provide type safety?",
                "Describe the Spring Boot auto-configuration mechanism.",
                "What are lambda expressions and functional interfaces in Java?",
                "How do you handle concurrency in a Java application?",
            ],
            "coding": [
                "Implement a thread-safe singleton pattern in Java.",
                "Write a Java program to reverse a linked list.",
                "Implement a producer-consumer pattern using wait/notify.",
                "Write a Java program to detect a cycle in a linked list.",
                "Implement an immutable class in Java.",
            ],
        },
        "node.js": {
            "technical": [
                "Explain the Node.js event loop architecture.",
                "What is the difference between process.nextTick and setImmediate?",
                "How does Node.js handle child processes?",
                "Describe the Streams API in Node.js.",
                "What is the difference between Cluster and Worker Threads?",
                "How do you handle uncaught exceptions in Node.js?",
                "Explain the purpose of package-lock.json.",
                "What are middleware functions in Express.js?",
                "How would you implement rate limiting in a Node.js application?",
                "Describe how to handle file streams efficiently in Node.js.",
            ],
            "coding": [
                "Write a Node.js script that reads a file line by line efficiently.",
                "Implement a simple HTTP server from scratch using only built-in modules.",
                "Write a custom readable stream in Node.js.",
                "Implement a task queue with concurrency control in Node.js.",
                "Write a file watcher that triggers actions on file changes.",
            ],
        },
        "docker": {
            "technical": [
                "Explain the difference between a Docker image and a container.",
                "What is a multi-stage Docker build? Why use it?",
                "Describe Docker networking modes.",
                "How do Docker volumes differ from bind mounts?",
                "What is Docker Compose and when would you use it?",
                "Explain the Dockerfile best practices for reducing image size.",
                "How does Docker handle logging?",
                "Describe Docker security best practices.",
                "What is the difference between CMD and ENTRYPOINT in a Dockerfile?",
                "How would you implement health checks in Docker?",
            ],
            "coding": [
                "Write a Dockerfile for a Python FastAPI application with multi-stage build.",
                "Create a docker-compose.yml for a 3-tier application.",
                "Write a Dockerfile that implements proper caching strategies for a Node.js app.",
                "Create a Docker network configuration for microservices.",
                "Write a script to clean up unused Docker resources.",
            ],
        },
        "kubernetes": {
            "technical": [
                "Explain the Kubernetes architecture and its main components.",
                "What is the difference between a Pod, Deployment, and StatefulSet?",
                "Describe Kubernetes Services and their types.",
                "How does the Kubernetes scheduler work?",
                "What are ConfigMaps and Secrets? How do they differ?",
                "Explain horizontal pod autoscaling.",
                "What are Init Containers and when would you use them?",
                "Describe Kubernetes RBAC and how it secures a cluster.",
            ],
            "coding": [
                "Write a Kubernetes deployment YAML for a microservice with readiness and liveness probes.",
                "Create a Helm chart for a multi-service application.",
                "Write a Kubernetes NetworkPolicy that restricts pod-to-pod communication.",
                "Implement a CronJob manifest that runs a database backup.",
            ],
        },
        "aws": {
            "technical": [
                "Explain the shared responsibility model in AWS.",
                "What are the differences between S3 storage classes?",
                "Describe AWS IAM best practices.",
                "How does AWS Lambda handle scaling?",
                "Explain the difference between SQS and SNS.",
                "What are VPCs and how do security groups differ from NACLs?",
                "Describe AWS CloudWatch and its use cases.",
                "What is the difference between RDS and Aurora?",
            ],
        },
        "machine learning": {
            "technical": [
                "Explain the bias-variance tradeoff in machine learning.",
                "What is the difference between supervised and unsupervised learning?",
                "Describe how a random forest algorithm works.",
                "What is cross-validation and why is it important?",
                "Explain gradient descent and its variants.",
                "What are the assumptions of linear regression?",
                "How do you handle imbalanced datasets?",
                "Describe the difference between L1 and L2 regularization.",
            ],
        },
    }

    # ─── Behavioral Questions ─────────────────────────────────────

    _BEHAVIORAL_QUESTIONS: dict[str, list[str]] = {
        "easy": [
            "Tell me about yourself and your professional background.",
            "Why are you interested in this position?",
            "What are your greatest strengths?",
            "Describe a time when you had to learn something new quickly.",
            "How do you prioritize your tasks when working on multiple projects?",
            "What motivates you at work?",
            "Describe your ideal work environment.",
            "Where do you see yourself in five years?",
        ],
        "medium": [
            "Tell me about a time you had a conflict with a coworker. How did you resolve it?",
            "Describe a situation where you had to make a difficult decision under pressure.",
            "Give an example of a project where you had to collaborate with multiple teams.",
            "Tell me about a time you failed. What did you learn from it?",
            "Describe a situation where you had to persuade someone to see things your way.",
            "Tell me about a time you went above and beyond what was expected of you.",
            "Describe how you handle constructive criticism.",
            "Give an example of when you demonstrated leadership skills.",
        ],
        "hard": [
            "Describe a situation where you had to balance competing priorities from different stakeholders.",
            "Tell me about a time you had to deliver bad news to a client or stakeholder.",
            "Give an example of when you identified a problem before it became critical.",
            "Describe a situation where you had to make a decision with incomplete information.",
            "Tell me about a time you had to change your approach mid-project.",
            "Give an example of when you mentored someone and the impact it had.",
            "Describe a situation where you had to manage up — influencing your manager's decisions.",
            "Tell me about a time you challenged the status quo and the outcome.",
        ],
    }

    # ─── HR Questions ─────────────────────────────────────────────

    _HR_QUESTIONS: list[str] = [
        "Why are you looking to leave your current position?",
        "What are your salary expectations for this role?",
        "How do you handle stress and tight deadlines?",
        "Are you comfortable with the work location/remote requirements?",
        "What is your notice period?",
        "Do you have any questions about our company culture?",
        "How do you stay updated with industry trends?",
        "What would your previous employer say about your work ethic?",
    ]

    # ─── Situational Questions ────────────────────────────────────

    _SITUATIONAL_QUESTIONS: dict[str, list[str]] = {
        "easy": [
            "How would you handle a situation where you disagree with a team decision?",
            "What would you do if you were assigned a task you've never done before?",
            "How would you handle receiving feedback you disagreed with?",
        ],
        "medium": [
            "If you discovered a critical bug in production on a Friday evening, what would you do?",
            "How would you handle a situation where a team member is not contributing their fair share?",
            "If you were given conflicting requirements from two stakeholders, how would you proceed?",
            "What would you do if you realized you couldn't meet a deadline?",
        ],
        "hard": [
            "If you had to choose between delivering a feature on time with technical debt or delaying the release, what would you do?",
            "How would you handle a situation where your technical lead made a decision you believe is wrong?",
            "If you were asked to work on a project outside your expertise with a tight deadline, how would you approach it?",
        ],
    }

    # ─── System Design Questions ──────────────────────────────────

    _SYSTEM_DESIGN_QUESTIONS: dict[str, list[str]] = {
        "medium": [
            "Design a URL shortening service like bit.ly.",
            "Design a real-time chat application.",
            "Design a news feed system like Twitter's timeline.",
            "Design a rate limiting system for an API.",
        ],
        "hard": [
            "Design a distributed file storage system like Dropbox.",
            "Design a ride-sharing service like Uber.",
            "Design a search autocomplete system.",
            "Design a distributed task scheduler.",
            "Design a video streaming platform like YouTube.",
        ],
    }

    # ─── Problem Solving Questions ────────────────────────────────

    _PROBLEM_SOLVING_QUESTIONS: dict[str, list[str]] = {
        "easy": [
            "How would you approach debugging a system that is running slower than expected?",
            "Describe your approach to writing unit tests for a new feature.",
            "How would you design a simple caching mechanism?",
        ],
        "medium": [
            "How would you design a system to handle 1 million concurrent users?",
            "Describe your approach to refactoring a legacy codebase.",
            "How would you implement a feature flag system?",
            "How would you design a logging and monitoring system for microservices?",
        ],
        "hard": [
            "How would you design a real-time analytics pipeline for processing 10 billion events per day?",
            "Describe how you would migrate a monolithic application to microservices without downtime.",
            "How would you design a consensus algorithm for a distributed system?",
        ],
    }

    # ─── Role Profiles (job-title → skill priority & seniority) ───

    _ROLE_PROFILES: dict[str, dict] = {
        "frontend": {
            "keywords": ("front-end", "frontend", "ui developer", "ui engineer",
                         "web designer", "web developer"),
            "priority_skills": ["react", "javascript"],
        },
        "backend": {
            "keywords": ("back-end", "backend", "api developer", "api engineer",
                         "server engineer", "platform developer"),
            "priority_skills": ["fastapi", "python", "node.js", "java", "sql"],
        },
        "fullstack": {
            "keywords": ("full-stack", "fullstack", "software engineer",
                         "software developer", "sde", "programmer"),
            "priority_skills": ["javascript", "react", "python", "sql"],
        },
        "data": {
            "keywords": ("data analyst", "data scientist", "data engineer",
                         "machine learning", "ml engineer", "ai engineer",
                         "business intelligence", "analytics"),
            "priority_skills": ["sql", "machine learning", "python"],
        },
        "devops": {
            "keywords": ("devops", "site reliability", "sre", "platform engineer",
                         "cloud engineer", "infrastructure engineer"),
            "priority_skills": ["docker", "kubernetes", "aws"],
        },
        "mobile": {
            "keywords": ("mobile developer", "android developer", "ios developer",
                         "react native", "flutter"),
            "priority_skills": ["javascript", "react"],
        },
    }

    _SENIOR_KEYWORDS = ("senior", "sr.", "sr ", "staff", "principal", "lead",
                        "architect", "head of", "expert", "specialist")

    # ─── Templates for skills outside the curated bank ────────────

    _TEMPLATE_TECHNICAL: dict[str, list[str]] = {
        "easy": [
            "What are the core concepts of {skill}, and how do they fit together?",
            "Describe your typical workflow when starting a new task that involves {skill}.",
            "What common mistakes do people make when learning {skill}, and how do you avoid them?",
        ],
        "medium": [
            "Describe a challenging real-world problem you solved using {skill}. What was your approach?",
            "How do you test, debug, and monitor solutions built with {skill} in production?",
            "What trade-offs do you weigh when choosing {skill} over alternatives for a project?",
        ],
        "hard": [
            "What are the biggest performance or scalability pitfalls when building with {skill}, and how have you addressed them?",
            "How would you evaluate whether {skill} is the right long-term choice for a high-traffic system?",
            "Walk me through the most complex architecture you have built around {skill} and the reasoning behind its key decisions.",
        ],
    }

    @classmethod
    def generate_questions(
        cls,
        job_title: str = "",
        job_description: str = "",
        required_skills: list[str] | None = None,
        preferred_skills: list[str] | None = None,
        experience_level: str = "",
        categories: list[str] | None = None,
        difficulty: str = "medium",
        count: int = 10,
        candidate_skills: list[str] | None = None,
        candidate_projects: list[str] | None = None,
        candidate_experience: list[str] | None = None,
    ) -> list[dict]:
        """Generate interview questions based on job + candidate context.

        Questions are levelled (easy/medium/hard) and driven by the job's
        role profile: title/description determine which skills are probed
        first and whether senior-level categories (system design, situational
        judgment) are mixed in.
        """
        all_skills = list(set((required_skills or []) + (preferred_skills or [])))
        candidate_skills = candidate_skills or []
        questions: list[dict] = []

        # Normalize requested difficulty (assessments allow "expert"; interviews don't).
        if not difficulty or difficulty == "expert":
            difficulty = "mixed" if not difficulty else "hard"
        if difficulty == "mixed":
            difficulties = ["easy", "medium", "hard"]
        elif difficulty in {"easy", "medium", "hard"}:
            difficulties = [difficulty]
        else:
            difficulties = ["medium"]

        extracted_skills = cls._extract_skills_from_text(
            f"{job_title} {job_description} {' '.join(all_skills)}"
        )
        role_name, priority_skills, senior = cls._detect_role(
            f"{job_title} {job_description} {experience_level}"
        )
        relevant_skills = cls._order_skills(
            list(set(extracted_skills + [s.lower() for s in all_skills])),
            priority_skills,
        )
        if not relevant_skills:
            relevant_skills = (
                cls._order_skills([s.lower() for s in candidate_skills[:5]], priority_skills)
                if candidate_skills
                else ["general"]
            )

        # Role-aware default mix when caller doesn't specify categories.
        if categories is None:
            categories = cls._default_categories(senior)
            allocations = cls._allocate(count, cls._category_weights(senior, categories))
        else:
            categories = list(categories)
            allocations = {cat: max(1, count // len(categories)) for cat in categories}

        for cat in categories:
            cat_count = allocations.get(cat, 0)
            if cat_count <= 0:
                continue
            if cat == "technical":
                questions.extend(cls._generate_technical(relevant_skills, difficulties, cat_count))
            elif cat == "behavioral":
                questions.extend(cls._generate_behavioral(difficulties, cat_count))
            elif cat == "hr":
                questions.extend(cls._generate_hr(cat_count))
            elif cat == "situational":
                questions.extend(cls._generate_situational(difficulties, cat_count))
            elif cat == "system_design":
                questions.extend(cls._generate_system_design(difficulties, cat_count))
            elif cat == "problem_solving":
                questions.extend(cls._generate_problem_solving(difficulties, cat_count))
            elif cat == "coding":
                questions.extend(cls._generate_coding(relevant_skills, difficulties, cat_count))

        if candidate_skills and "technical" in categories:
            questions.extend(cls._generate_personalized(candidate_skills, candidate_projects, candidate_experience, difficulties))

        random.shuffle(questions)
        return questions[:count]

    # ─── Role Detection ───────────────────────────────────────────

    @classmethod
    def _detect_role(cls, text: str) -> tuple[str, list[str], bool]:
        """Return (role_name, prioritized_skills, is_senior) from job text."""
        text_lower = text.lower()
        role_name = ""
        priority_skills: list[str] = []
        for name, profile in cls._ROLE_PROFILES.items():
            if any(kw in text_lower for kw in profile["keywords"]):
                role_name = name
                priority_skills = list(profile["priority_skills"])
                break

        senior = any(kw in text_lower for kw in cls._SENIOR_KEYWORDS)
        years = [int(m) for m in re.findall(r"(\d+)\s*\+?\s*(?:to\s*\d+\s*)?years?", text_lower)]
        if years and max(years) >= 5:
            senior = True
        return role_name, priority_skills, senior

    @classmethod
    def _order_skills(cls, skills: list[str], priority: list[str]) -> list[str]:
        """Order skills so role-priority skills come first."""
        prio_lower = [p.lower() for p in priority]
        ranked = sorted(
            set(skills),
            key=lambda s: prio_lower.index(s.lower()) if s.lower() in prio_lower else len(prio_lower),
        )
        return ranked

    @classmethod
    def _default_categories(cls, senior: bool) -> list[str]:
        base = ["technical", "behavioral", "problem_solving", "situational"]
        if senior:
            base.append("system_design")
        return base

    @classmethod
    def _category_weights(cls, senior: bool, categories: list[str]) -> dict[str, float]:
        if senior:
            weights = {
                "technical": 0.40,
                "system_design": 0.20,
                "problem_solving": 0.15,
                "behavioral": 0.15,
                "situational": 0.10,
            }
        else:
            weights = {
                "technical": 0.50,
                "behavioral": 0.25,
                "problem_solving": 0.15,
                "situational": 0.10,
            }
        return {cat: weights.get(cat, 0.1) for cat in categories}

    @staticmethod
    def _allocate(total: int, weights: dict[str, float]) -> dict[str, int]:
        """Largest-remainder split so every category gets representation."""
        weight_sum = sum(weights.values()) or 1.0
        raw = {cat: total * w / weight_sum for cat, w in weights.items()}
        alloc = {cat: int(v) for cat, v in raw.items()}
        remainder = total - sum(alloc.values())
        by_frac = sorted(raw, key=lambda c: raw[c] - alloc[c], reverse=True)
        for cat in by_frac[:remainder]:
            alloc[cat] += 1
        return alloc

    @classmethod
    def _extract_skills_from_text(cls, text: str) -> list[str]:
        """Extract known skills from free text."""
        text_lower = text.lower()
        found = []
        for skill in cls._SKILL_QUESTIONS:
            if skill in text_lower:
                found.append(skill)
        aliases = {
            "js": "javascript", "ts": "javascript", "typescript": "javascript",
            "py": "python", "k8s": "kubernetes", "k8": "kubernetes",
            "reactjs": "react", "react.js": "react",
            "node": "node.js", "nodejs": "node.js",
            "fastapi": "fastapi", "fast api": "fastapi",
            "postgres": "sql", "postgresql": "sql", "mysql": "sql", "sqlite": "sql",
            "ml": "machine learning", "ai": "machine learning",
        }
        for alias, canonical in aliases.items():
            if alias in text_lower and canonical not in found:
                found.append(canonical)
        return found

    @classmethod
    def _generate_technical(cls, skills: list[str], difficulties: list[str], count: int) -> list[dict]:
        questions: list[dict] = []
        seen_texts: set[str] = set()
        multi_level = len(difficulties) > 1

        for skill in skills:
            skill_lower = skill.lower() if skill != "general" else skill
            # Curated bank questions (level assigned round-robin when mixed).
            pool = list(cls._SKILL_QUESTIONS.get(skill_lower, {}).get("technical", []))
            random.shuffle(pool)
            items: list[tuple[str, str]] = [
                (q, difficulties[i % len(difficulties)] if multi_level else difficulties[0])
                for i, q in enumerate(pool)
            ]
            # Level-appropriate templates guarantee coverage for ANY skill.
            if not pool or len(items) < count:
                for diff in difficulties:
                    for tmpl in cls._TEMPLATE_TECHNICAL.get(diff, []):
                        items.append((tmpl.format(skill=skill), diff))

            for text, level in items:
                key = text.lower()
                if key in seen_texts:
                    continue
                seen_texts.add(key)
                questions.append({
                    "question_text": text,
                    "category": "technical",
                    "difficulty": level,
                    "context": {"skill": skill, "type": "technical"},
                })

        random.shuffle(questions)
        return questions[:count]

    @classmethod
    def _generate_behavioral(cls, difficulties: list[str], count: int) -> list[dict]:
        questions = []
        for diff in difficulties:
            pool = cls._BEHAVIORAL_QUESTIONS.get(diff, cls._BEHAVIORAL_QUESTIONS.get("medium", []))
            for q in pool:
                questions.append({
                    "question_text": q,
                    "category": "behavioral",
                    "difficulty": diff,
                    "context": {"type": "behavioral"},
                })
        random.shuffle(questions)
        return questions[:count]

    @classmethod
    def _generate_hr(cls, count: int) -> list[dict]:
        pool = list(cls._HR_QUESTIONS)
        random.shuffle(pool)
        return [
            {
                "question_text": q,
                "category": "hr",
                "difficulty": "easy",
                "context": {"type": "hr"},
            }
            for q in pool[:count]
        ]

    @staticmethod
    def _dedupe_append(
        questions: list[dict],
        items: list[dict],
        seen_texts: set[str],
    ) -> None:
        for item in items:
            key = item["question_text"].lower()
            if key in seen_texts:
                continue
            seen_texts.add(key)
            questions.append(item)

    @classmethod
    def _generate_situational(cls, difficulties: list[str], count: int) -> list[dict]:
        questions: list[dict] = []
        seen: set[str] = set()
        for diff in difficulties:
            pool = cls._SITUATIONAL_QUESTIONS.get(diff, [])
            cls._dedupe_append(questions, [{
                "question_text": q,
                "category": "situational",
                "difficulty": diff,
                "context": {"type": "situational"},
            } for q in pool], seen)
        # Supplement with the assessment engine's situational-judgment bank.
        try:
            from app.services.assessment.question_banks import SITUATIONAL_JUDGMENT_BANK
            cls._dedupe_append(questions, [{
                "question_text": item["question_text"],
                "category": "situational",
                "difficulty": item.get("difficulty", "medium"),
                "context": {"type": "situational", "topic": item.get("topic")},
            } for item in SITUATIONAL_JUDGMENT_BANK
                if item.get("difficulty") in difficulties], seen)
        except ImportError:
            pass
        random.shuffle(questions)
        return questions[:count]

    @classmethod
    def _generate_system_design(cls, difficulties: list[str], count: int) -> list[dict]:
        questions: list[dict] = []
        seen: set[str] = set()
        for diff in difficulties:
            pool = cls._SYSTEM_DESIGN_QUESTIONS.get(diff, [])
            cls._dedupe_append(questions, [{
                "question_text": q,
                "category": "system_design",
                "difficulty": diff,
                "context": {"type": "system_design"},
            } for q in pool], seen)
        # Deeper prompts from the assessment engine's bank.
        try:
            from app.services.assessment.question_banks import SYSTEM_DESIGN_PROMPTS
            for diff in difficulties:
                for item in SYSTEM_DESIGN_PROMPTS.get(diff, []):
                    cls._dedupe_append(questions, [{
                        "question_text": item["prompt"],
                        "category": "system_design",
                        "difficulty": diff,
                        "context": {"type": "system_design", "rubric": item.get("rubric")},
                    }], seen)
        except ImportError:
            pass
        random.shuffle(questions)
        return questions[:count]

    @classmethod
    def _generate_problem_solving(cls, difficulties: list[str], count: int) -> list[dict]:
        questions: list[dict] = []
        seen: set[str] = set()
        for diff in difficulties:
            pool = cls._PROBLEM_SOLVING_QUESTIONS.get(diff, [])
            cls._dedupe_append(questions, [{
                "question_text": q,
                "category": "problem_solving",
                "difficulty": diff,
                "context": {"type": "problem_solving"},
            } for q in pool], seen)
        # Scenario / case-study banks give role-flavored depth.
        try:
            from app.services.assessment.question_banks import (
                CASE_STUDY_BANK,
                SCENARIO_BANK,
            )
            for bank in (SCENARIO_BANK, CASE_STUDY_BANK):
                cls._dedupe_append(questions, [{
                    "question_text": item["question_text"],
                    "category": "problem_solving",
                    "difficulty": item.get("difficulty", "medium"),
                    "context": {"type": "problem_solving", "topic": item.get("topic"),
                                "skill_area": item.get("skill")},
                } for item in bank
                    if item.get("difficulty") in difficulties], seen)
        except ImportError:
            pass
        random.shuffle(questions)
        return questions[:count]

    @classmethod
    def _generate_coding(cls, skills: list[str], difficulties: list[str], count: int) -> list[dict]:
        questions = []
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower in cls._SKILL_QUESTIONS:
                for diff in difficulties:
                    pool = cls._SKILL_QUESTIONS[skill_lower].get("coding", [])
                    for q in pool:
                        questions.append({
                            "question_text": q,
                            "category": "coding",
                            "difficulty": diff,
                            "context": {"skill": skill, "type": "coding"},
                        })
        random.shuffle(questions)
        return questions[:count]

    @classmethod
    def _generate_personalized(
        cls,
        candidate_skills: list[str],
        candidate_projects: list[str] | None,
        candidate_experience: list[str] | None,
        difficulties: list[str],
    ) -> list[dict]:
        questions = []
        for skill in candidate_skills[:3]:
            skill_lower = skill.lower()
            if skill_lower in cls._SKILL_QUESTIONS:
                pool = cls._SKILL_QUESTIONS[skill_lower].get("technical", [])
                if pool:
                    q = random.choice(pool)
                    questions.append({
                        "question_text": f"Based on your experience with {skill}: {q}",
                        "category": "technical",
                        "difficulty": random.choice(difficulties),
                        "context": {"skill": skill, "personalized": True, "type": "technical"},
                    })
        if candidate_projects:
            proj = random.choice(candidate_projects)
            questions.append({
                "question_text": f"Tell me about the project '{proj}'. What were the main technical challenges and how did you overcome them?",
                "category": "behavioral",
                "difficulty": "medium",
                "context": {"project": proj, "personalized": True, "type": "behavioral"},
            })
        return questions
