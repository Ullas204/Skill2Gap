"""AI Answer Evaluation Engine.

Rule-based evaluation of interview answers using keyword analysis,
structure detection, length heuristics, and confidence scoring.
"""

from __future__ import annotations

import re


class AnswerEvaluator:
    _HEDGING_WORDS = {
        "maybe", "perhaps", "i think", "i guess", "probably", "not sure",
        "i suppose", "i might", "sort of", "kind of", "i feel like",
        "possibly", "it depends", "generally speaking",
    }

    _CONFIDENCE_WORDS = {
        "definitely", "certainly", "absolutely", "specifically",
        "in my experience", "i have", "i implemented", "i built",
        "i designed", "i developed", "i led", "i created",
        "the best approach is", "the correct way", "always", "never",
    }

    _TECHNICAL_KEYWORDS: dict[str, list[str]] = {
        "python": ["class", "def", "import", "list", "dict", "tuple", "set", "lambda",
                    "decorator", "generator", "async", "await", "yield", "self",
                    "comprehension", "gil", "metaclass", "abc", "exception", "try", "except"],
        "javascript": ["function", "const", "let", "var", "async", "await", "promise",
                        "callback", "closure", "prototype", "this", "arrow", "spread",
                        "destructuring", "template", "module", "import", "export"],
        "react": ["component", "state", "props", "hook", "usestate", "useeffect",
                   "usecallback", "usememo", "usecontext", "reducer", "lifecycle",
                   "virtual dom", "jsx", "render", "memo", "ref", "context"],
        "fastapi": ["endpoint", "router", "dependency", "pydantic", "async",
                     "middleware", "background task", "websocket", "openapi",
                     "path parameter", "query parameter", "body"],
        "sql": ["select", "join", "where", "group by", "having", "order by",
                "index", "transaction", "acid", "normalization", "cte", "window"],
        "java": ["class", "interface", "extends", "implements", "generic",
                 "stream", "optional", "thread", "synchronized", "volatile",
                 "annotation", "spring", "bean", "autowired"],
        "node.js": ["event loop", "callback", "stream", "buffer", "module",
                     "require", "express", "middleware", "cluster", "worker"],
        "docker": ["image", "container", "dockerfile", "volume", "network",
                    "compose", "layer", "build", "push", "pull", "registry"],
        "kubernetes": ["pod", "deployment", "service", "configmap", "secret",
                        "ingress", "node", "cluster", "replica", "hpa", "rbac"],
        "aws": ["s3", "ec2", "lambda", "iam", "vpc", "rds", "cloudwatch",
                 "sqs", "sns", "dynamodb", "cloudformation"],
        "machine learning": ["model", "training", "validation", "test", "loss",
                              "gradient", "overfitting", "underfitting", "feature",
                              "accuracy", "precision", "recall", "cross-validation"],
    }

    _POSITIVE_STRUCTURAL_MARKERS = [
        r"\bfor example\b", r"\bsuch as\b", r"\bfor instance\b",
        r"\bin my experience\b", r"\bspecifically\b", r"\bstep \d\b",
        r"\bfirst\b.*\bsecond\b", r"\bpros?\b.*\bcons?\b",
        r"\btrade-?off\b", r"\bbecause\b", r"\btherefore\b",
        r"\bhowever\b", r"\bin contrast\b", r"\balternatively\b",
    ]

    @classmethod
    def evaluate_answer(
        cls,
        question_text: str,
        answer_text: str,
        category: str = "technical",
        question_context: dict | None = None,
    ) -> dict:
        """Evaluate an interview answer and return scores + feedback."""
        answer_lower = answer_text.lower().strip()
        word_count = len(answer_text.split())
        skill = (question_context or {}).get("skill", "")

        technical_accuracy = cls._score_technical_accuracy(answer_lower, category, skill)
        completeness = cls._score_completeness(answer_text, category)
        communication = cls._score_communication(answer_text, word_count)
        problem_solving = cls._score_problem_solving(answer_text, category)
        confidence = cls._score_confidence(answer_lower)
        relevance = cls._score_relevance(answer_lower, question_text)

        overall = cls._calculate_overall(
            technical_accuracy, completeness, communication,
            problem_solving, confidence, relevance, category,
        )

        feedback = cls._generate_feedback(
            overall, technical_accuracy, completeness, communication,
            confidence, relevance, category,
        )
        suggestions = cls._generate_suggestions(
            technical_accuracy, completeness, communication, confidence, relevance
        )
        follow_ups = cls._generate_follow_ups(category, overall, skill)

        return {
            "technical_accuracy": technical_accuracy,
            "completeness": completeness,
            "communication": communication,
            "problem_solving": problem_solving,
            "confidence": confidence,
            "relevance": relevance,
            "overall_score": overall,
            "feedback": feedback,
            "improvement_suggestions": suggestions,
            "follow_up_questions": follow_ups,
        }

    @classmethod
    def _score_technical_accuracy(cls, answer_lower: str, category: str, skill: str) -> int:
        if category not in ("technical", "coding", "system_design"):
            return min(70, max(40, len(answer_lower.split()) * 2))

        score = 30
        keywords = cls._TECHNICAL_KEYWORDS.get(skill.lower(), [])
        if keywords:
            found = sum(1 for kw in keywords if kw in answer_lower)
            keyword_pct = min(found / max(len(keywords) * 0.3, 1), 1.0)
            score += int(keyword_pct * 50)

        technical_patterns = [
            r"\b(algorithm|complexity|o\(n\)|time|space)\b",
            r"\b(api|database|server|client|request|response)\b",
            r"\b(error|exception|try|catch|handle)\b",
            r"\b(pattern|architecture|design|structure)\b",
            r"\b(test|assert|verify|validate)\b",
        ]
        pattern_hits = sum(1 for p in technical_patterns if re.search(p, answer_lower))
        score += min(pattern_hits * 5, 20)

        return min(score, 100)

    @classmethod
    def _score_completeness(cls, answer_text: str, category: str) -> int:
        word_count = len(answer_text.split())
        score = 20
        if word_count >= 20:
            score += 15
        if word_count >= 50:
            score += 15
        if word_count >= 100:
            score += 10
        if word_count >= 200:
            score += 10

        structural_score = 0
        for pattern in cls._POSITIVE_STRUCTURAL_MARKERS:
            if re.search(pattern, answer_text.lower()):
                structural_score += 8
        score += min(structural_score, 25)

        paragraphs = [p.strip() for p in answer_text.split("\n\n") if p.strip()]
        if len(paragraphs) >= 2:
            score += 10

        if category in ("system_design", "problem_solving") and word_count < 100:
            score = max(score - 15, 20)

        return min(score, 100)

    @classmethod
    def _score_communication(cls, answer_text: str, word_count: int) -> int:
        score = 40

        sentences = re.split(r'[.!?]+', answer_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_len <= 25:
                score += 20
            elif avg_len < 10:
                score += 10
            else:
                score += 5

        has_structure = bool(re.search(r'\n\n|\t|^\s*[-•*]\s', answer_text, re.MULTILINE))
        if has_structure:
            score += 15

        filler_words = ["um", "uh", "like", "you know", "basically", "actually"]
        filler_count = sum(answer_text.lower().count(fw) for fw in filler_words)
        score -= min(filler_count * 3, 15)

        if word_count > 5:
            sentences_count = max(len(re.split(r'[.!?]+', answer_text)) - 1, 1)
            words_per_sentence = word_count / sentences_count
            if 8 <= words_per_sentence <= 30:
                score += 10

        return min(max(score, 20), 100)

    @classmethod
    def _score_problem_solving(cls, answer_text: str, category: str) -> int:
        score = 30
        answer_lower = answer_text.lower()

        if any(w in answer_lower for w in ["approach", "strategy", "step", "first", "then", "finally"]):
            score += 15

        if any(w in answer_lower for w in ["trade-off", "tradeoff", "pros", "cons", "alternative", "instead"]):
            score += 15

        if any(w in answer_lower for w in ["if", "scenario", "case", "situation", "depending"]):
            score += 10

        if any(w in answer_lower for w in ["consider", "evaluate", "analyze", "compare", "assess"]):
            score += 10

        if category in ("problem_solving", "system_design"):
            if any(w in answer_lower for w in ["scalability", "performance", "reliability", "availability"]):
                score += 10
            if any(w in answer_lower for w in ["bottleneck", "optimize", "cache", "load balanc"]):
                score += 10

        return min(score, 100)

    @classmethod
    def _score_confidence(cls, answer_lower: str) -> int:
        score = 50

        hedge_count = sum(1 for hw in cls._HEDGING_WORDS if hw in answer_lower)
        score -= min(hedge_count * 5, 20)

        conf_count = sum(1 for cw in cls._CONFIDENCE_WORDS if cw in answer_lower)
        score += min(conf_count * 5, 30)

        has_examples = bool(re.search(r"\b(example|instance|such as|like when|i once|i have)\b", answer_lower))
        if has_examples:
            score += 10

        return min(max(score, 20), 100)

    @classmethod
    def _score_relevance(cls, answer_lower: str, question_text: str) -> int:
        q_words = set(re.findall(r'\b\w{3,}\b', question_text.lower()))
        q_words -= {"what", "how", "why", "when", "where", "which", "tell", "about",
                     "describe", "explain", "give", "the", "and", "for", "are", "you",
                     "your", "this", "that", "with", "from", "have", "has", "can", "did"}
        if not q_words:
            return 60

        answer_words = set(answer_lower.split())
        overlap = q_words & answer_words
        if q_words:
            relevance_pct = len(overlap) / len(q_words)
        else:
            relevance_pct = 0.5

        score = 40 + int(relevance_pct * 50)
        return min(max(score, 30), 100)

    @classmethod
    def _calculate_overall(
        cls, technical: int, completeness: int, communication: int,
        problem_solving: int, confidence: int, relevance: int, category: str,
    ) -> int:
        weights = {
            "technical": {"technical_accuracy": 0.30, "completeness": 0.20, "communication": 0.15, "problem_solving": 0.15, "confidence": 0.10, "relevance": 0.10},
            "coding": {"technical_accuracy": 0.35, "completeness": 0.20, "communication": 0.10, "problem_solving": 0.20, "confidence": 0.05, "relevance": 0.10},
            "behavioral": {"technical_accuracy": 0.05, "completeness": 0.25, "communication": 0.25, "problem_solving": 0.15, "confidence": 0.15, "relevance": 0.15},
            "hr": {"technical_accuracy": 0.05, "completeness": 0.20, "communication": 0.30, "problem_solving": 0.10, "confidence": 0.20, "relevance": 0.15},
            "situational": {"technical_accuracy": 0.10, "completeness": 0.20, "communication": 0.20, "problem_solving": 0.25, "confidence": 0.10, "relevance": 0.15},
            "system_design": {"technical_accuracy": 0.25, "completeness": 0.25, "communication": 0.15, "problem_solving": 0.25, "confidence": 0.05, "relevance": 0.05},
            "problem_solving": {"technical_accuracy": 0.15, "completeness": 0.20, "communication": 0.15, "problem_solving": 0.30, "confidence": 0.10, "relevance": 0.10},
        }
        w = weights.get(category, weights["technical"])
        overall = (
            technical * w["technical_accuracy"]
            + completeness * w["completeness"]
            + communication * w["communication"]
            + problem_solving * w["problem_solving"]
            + confidence * w["confidence"]
            + relevance * w["relevance"]
        )
        return min(round(overall), 100)

    @classmethod
    def _generate_feedback(
        cls, overall: int, technical: int, completeness: int,
        communication: int, confidence: int, relevance: int, category: str,
    ) -> str:
        parts = []
        if overall >= 80:
            parts.append("Excellent response. You demonstrated strong knowledge and clear communication.")
        elif overall >= 60:
            parts.append("Good response with room for improvement in some areas.")
        elif overall >= 40:
            parts.append("Adequate response, but there are significant areas that could be strengthened.")
        else:
            parts.append("The response needs substantial improvement across multiple dimensions.")

        if technical < 50 and category in ("technical", "coding"):
            parts.append("Technical accuracy could be improved with more specific details and examples.")
        if completeness < 50:
            parts.append("The answer could be more comprehensive. Consider providing more detail or examples.")
        if communication < 50:
            parts.append("Consider structuring your answer more clearly with distinct points.")
        if confidence < 50:
            parts.append("Try to sound more definitive. Avoid excessive hedging language.")
        if relevance < 50:
            parts.append("Try to stay more focused on the specific question being asked.")

        return " ".join(parts)

    @classmethod
    def _generate_suggestions(
        cls, technical: int, completeness: int, communication: int,
        confidence: int, relevance: int,
    ) -> list[str]:
        suggestions = []
        if technical < 60:
            suggestions.append("Review core concepts and practice explaining them with concrete examples")
        if completeness < 60:
            suggestions.append("Structure your answer with clear beginning, middle, and conclusion")
            suggestions.append("Provide specific examples to support your points")
        if communication < 60:
            suggestions.append("Practice articulating complex ideas in simple, clear language")
            suggestions.append("Use bullet points or numbered steps to organize your thoughts")
        if confidence < 60:
            suggestions.append("Reduce hedging language and speak with more conviction")
            suggestions.append("Back up your statements with concrete experiences")
        if relevance < 60:
            suggestions.append("Listen carefully to the question and address it directly before elaborating")
        if not suggestions:
            suggestions.append("Continue practicing to maintain your strong performance")
        return suggestions

    @classmethod
    def _generate_follow_ups(cls, category: str, overall: int, skill: str) -> list[str]:
        follow_ups = []
        if category == "technical":
            if overall < 60:
                follow_ups.append(f"Can you provide a more detailed explanation of {skill if skill else 'this concept'}?")
            follow_ups.append("How would you apply this in a production environment?")
            follow_ups.append("What are the potential pitfalls or edge cases to consider?")
        elif category == "behavioral":
            follow_ups.append("What was the specific outcome of that situation?")
            follow_ups.append("What would you do differently if faced with the same situation again?")
        elif category == "system_design":
            follow_ups.append("How would you handle failure scenarios in this design?")
            follow_ups.append("What metrics would you use to measure the success of this system?")
        elif category == "coding":
            follow_ups.append("What is the time and space complexity of your solution?")
            follow_ups.append("How would you optimize this further?")
        else:
            follow_ups.append("Can you elaborate on that with a specific example?")
        return follow_ups
