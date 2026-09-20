"""Tests for Phase 8 – Interview Intelligence Platform."""

import pytest
from app.services.interview.question_generator import QuestionGenerator
from app.services.interview.answer_evaluator import AnswerEvaluator
from app.services.interview.coding_engine import CodingEngine
from app.services.interview.scorecard_engine import ScorecardEngine


class TestQuestionGenerator:
    def test_generate_technical_questions(self):
        questions = QuestionGenerator.generate_questions(
            required_skills=["python", "react"],
            categories=["technical"],
            difficulty="medium",
            count=5,
        )
        assert len(questions) <= 5
        assert all(q["category"] == "technical" for q in questions)
        assert all(q["difficulty"] == "medium" for q in questions)

    def test_generate_behavioral_questions(self):
        questions = QuestionGenerator.generate_questions(
            categories=["behavioral"],
            difficulty="easy",
            count=3,
        )
        assert len(questions) <= 3
        assert all(q["category"] == "behavioral" for q in questions)

    def test_generate_mixed_difficulty(self):
        questions = QuestionGenerator.generate_questions(
            required_skills=["python"],
            categories=["technical", "behavioral"],
            difficulty="mixed",
            count=10,
        )
        assert len(questions) <= 10
        categories = set(q["category"] for q in questions)
        assert "technical" in categories or "behavioral" in categories

    def test_generate_with_job_description(self):
        questions = QuestionGenerator.generate_questions(
            job_title="Senior Python Developer",
            job_description="We need a Python developer with FastAPI and PostgreSQL experience",
            categories=["technical"],
            count=5,
        )
        assert len(questions) <= 5
        assert any("python" in q["question_text"].lower() or
                   "fastapi" in q["question_text"].lower() or
                   "sql" in q["question_text"].lower()
                   for q in questions)

    def test_generate_personalized_questions(self):
        questions = QuestionGenerator.generate_questions(
            categories=["technical"],
            candidate_skills=["python", "react"],
            candidate_projects=["E-commerce Platform"],
            count=3,
        )
        assert len(questions) <= 3

    def test_extract_skills_from_text(self):
        skills = QuestionGenerator._extract_skills_from_text("Python FastAPI Docker PostgreSQL")
        assert "python" in skills
        assert "fastapi" in skills
        assert "docker" in skills
        assert "sql" in skills

    def test_empty_categories_returns_minimal(self):
        questions = QuestionGenerator.generate_questions(
            categories=["hr"],
            count=5,
        )
        assert len(questions) <= 5
        assert all(q["category"] == "hr" for q in questions)


class TestAnswerEvaluator:
    def test_evaluate_strong_technical_answer(self):
        answer = (
            "In Python, decorators are functions that modify other functions. "
            "For example, I implemented a caching decorator using functools.lru_cache "
            "in a production FastAPI application. The decorator wraps the function and "
            "stores results, reducing database queries. Specifically, it reduced our "
            "API response time by 40%. The implementation uses @wraps from functools "
            "to preserve the original function metadata. In my experience, decorators "
            "are excellent for cross-cutting concerns like logging and authentication."
        )
        result = AnswerEvaluator.evaluate_answer(
            question_text="What are decorators in Python?",
            answer_text=answer,
            category="technical",
            question_context={"skill": "python"},
        )
        assert result["overall_score"] >= 50
        assert result["technical_accuracy"] > 30
        assert result["confidence"] > 40
        assert result["feedback"] is not None
        assert isinstance(result["improvement_suggestions"], list)

    def test_evaluate_weak_answer(self):
        result = AnswerEvaluator.evaluate_answer(
            question_text="Explain React hooks",
            answer_text="I think maybe hooks are like, functions you use in React?",
            category="technical",
            question_context={"skill": "react"},
        )
        assert result["overall_score"] < 60
        assert result["confidence"] < 60

    def test_evaluate_empty_answer(self):
        result = AnswerEvaluator.evaluate_answer(
            question_text="Tell me about yourself",
            answer_text="",
            category="behavioral",
        )
        assert result["overall_score"] <= 40

    def test_evaluate_behavioral_answer(self):
        answer = (
            "In my previous role, I had a conflict with a senior developer about "
            "the architecture of a new microservice. First, I scheduled a one-on-one "
            "meeting to understand their perspective. I listened actively and realized "
            "their concerns about scalability were valid. I then proposed a compromise "
            "that combined both approaches. For example, we used their event-driven "
            "pattern for the communication layer, and my suggested REST API for the "
            "external interfaces. The result was a system that handled 3x more traffic "
            "than either original proposal. This experience taught me the value of "
            "collaborative problem-solving."
        )
        result = AnswerEvaluator.evaluate_answer(
            question_text="Tell me about a time you had a conflict with a coworker",
            answer_text=answer,
            category="behavioral",
        )
        assert result["overall_score"] >= 50
        assert result["communication"] > 40

    def test_evaluate_coding_answer(self):
        answer = """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Time complexity: O(n)
# Space complexity: O(n)
# Edge cases: empty array, single element"""
        result = AnswerEvaluator.evaluate_answer(
            question_text="Write a two-sum function",
            answer_text=answer,
            category="coding",
            question_context={"skill": "python"},
        )
        assert result["overall_score"] >= 40
        assert result["technical_accuracy"] > 30

    def test_scores_are_in_range(self):
        result = AnswerEvaluator.evaluate_answer(
            question_text="Test question",
            answer_text="This is a test answer with some content to evaluate properly.",
            category="hr",
        )
        for key in ["technical_accuracy", "completeness", "communication",
                     "problem_solving", "confidence", "relevance", "overall_score"]:
            assert 0 <= result[key] <= 100


class TestCodingEngine:
    def test_generate_coding_problems(self):
        problems = CodingEngine.generate_assessments(
            difficulty="easy",
            category="coding",
            count=2,
        )
        assert len(problems) == 2
        assert all(p["difficulty"] == "easy" for p in problems)
        assert all("problem_title" in p for p in problems)

    def test_generate_mcq_problems(self):
        problems = CodingEngine.generate_assessments(
            difficulty="medium",
            category="mcq",
            count=2,
        )
        assert len(problems) == 2
        assert all(p["category"] == "mcq" for p in problems)

    def test_generate_sql_problems(self):
        problems = CodingEngine.generate_assessments(
            difficulty="medium",
            category="sql",
            count=2,
        )
        assert len(problems) == 2

    def test_evaluate_correct_mcq(self):
        result = CodingEngine.evaluate_submission(
            solution="B",
            test_cases=[{"expected": "B"}],
            category="mcq",
        )
        assert result["is_correct"] is True
        assert result["score"] == 100

    def test_evaluate_incorrect_mcq(self):
        result = CodingEngine.evaluate_submission(
            solution="A",
            test_cases=[{"expected": "B"}],
            category="mcq",
        )
        assert result["is_correct"] is False
        assert result["score"] == 0

    def test_evaluate_sql_solution(self):
        result = CodingEngine.evaluate_submission(
            solution="SELECT department, AVG(salary) FROM employees GROUP BY department ORDER BY AVG(salary) DESC LIMIT 1",
            test_cases=[{"expected": "SELECT department, AVG(salary) FROM employees GROUP BY department"}],
            category="sql",
        )
        assert result["score"] > 50

    def test_evaluate_coding_solution(self):
        result = CodingEngine.evaluate_submission(
            solution="""def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
# Time complexity: O(n)
# Space complexity: O(n)""",
            test_cases=[{"input": "[2,7,11,15], target=9", "expected": "[0,1]"}],
            category="coding",
        )
        assert result["score"] > 40

    def test_no_test_cases_returns_partial_credit(self):
        result = CodingEngine.evaluate_submission(
            solution="def solve(): return 42",
            test_cases=[],
            category="coding",
        )
        assert result["score"] > 0


class TestScorecardEngine:
    def test_determine_recommendation(self):
        assert ScorecardEngine._determine_recommendation(85) == "strongly_recommend"
        assert ScorecardEngine._determine_recommendation(70) == "recommend"
        assert ScorecardEngine._determine_recommendation(50) == "consider"
        assert ScorecardEngine._determine_recommendation(30) == "not_recommended"

    def test_calculate_hiring_confidence(self):
        from unittest.mock import MagicMock
        eval1 = MagicMock()
        eval1.overall_score = 75
        eval2 = MagicMock()
        eval2.overall_score = 80

        confidence = ScorecardEngine._calculate_hiring_confidence(
            [eval1, eval2],
            {"overall_score": 77},
        )
        assert 0 <= confidence <= 100
        assert confidence > 50

    def test_generate_summary(self):
        from unittest.mock import MagicMock
        eval1 = MagicMock()
        eval1.overall_score = 75

        summary = ScorecardEngine._generate_summary(
            {"overall_score": 77, "technical_skills": 80, "communication": 70, "problem_solving": 75},
            5,
            MagicMock(),
        )
        assert isinstance(summary, str)
        assert len(summary) > 0
