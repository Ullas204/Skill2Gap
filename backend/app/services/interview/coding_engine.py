"""AI Coding Assessment Engine."""

from __future__ import annotations

import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interview.interview import CodingAssessmentRepository


class CodingEngine:
    _CODING_PROBLEMS: dict[str, list[dict]] = {
        "easy": [
            {
                "title": "Two Sum",
                "description": "Given an array of integers and a target, return indices of two numbers that add up to the target. Discuss your approach and complexity.",
                "category": "coding",
                "test_cases": [
                    {"input": "[2,7,11,15], target=9", "expected": "[0,1]"},
                    {"input": "[3,2,4], target=6", "expected": "[1,2]"},
                ],
            },
            {
                "title": "Reverse String",
                "description": "Write a function to reverse a string in-place. Analyze the time and space complexity.",
                "category": "coding",
                "test_cases": [
                    {"input": "hello", "expected": "olleh"},
                    {"input": "abcd", "expected": "dcba"},
                ],
            },
            {
                "title": "FizzBuzz Plus",
                "description": "Write a function that prints numbers 1 to n. For multiples of 3 print 'Fizz', for 5 print 'Buzz', for both print 'FizzBuzz'. For prime numbers print 'Prime'.",
                "category": "coding",
                "test_cases": [
                    {"input": "15", "expected": "1,2,Prime,4,Fizz,Buzz,Prime,8,Fizz,Prime,11,Fizz,Prime,13,FizzBuzz"},
                ],
            },
            {
                "title": "Find Missing Number",
                "description": "Given an array containing n distinct numbers from 0 to n, find the missing number.",
                "category": "coding",
                "test_cases": [
                    {"input": "[3,0,1]", "expected": "2"},
                    {"input": "[0,1]", "expected": "2"},
                ],
            },
        ],
        "medium": [
            {
                "title": "LRU Cache",
                "description": "Design and implement a Least Recently Used (LRU) cache with O(1) get and put operations. Discuss your design choices.",
                "category": "coding",
                "test_cases": [
                    {"input": "put(1,1), put(2,2), get(1), put(3,3), get(2)", "expected": "1, null"},
                ],
            },
            {
                "title": "Binary Tree Level Order Traversal",
                "description": "Given a binary tree, return the level order traversal of its nodes' values as a list of lists.",
                "category": "coding",
                "test_cases": [
                    {"input": "[3,9,20,null,null,15,7]", "expected": "[[3],[9,20],[15,7]]"},
                ],
            },
            {
                "title": "Merge Intervals",
                "description": "Given a collection of intervals, merge all overlapping intervals.",
                "category": "coding",
                "test_cases": [
                    {"input": "[[1,3],[2,6],[8,10],[15,18]]", "expected": "[[1,6],[8,10],[15,18]]"},
                ],
            },
            {
                "title": "Design a Rate Limiter",
                "description": "Implement a rate limiter that limits the number of requests a user can make in a given time window. Support different limits per endpoint.",
                "category": "coding",
                "test_cases": [
                    {"input": "window=60s, limit=10, 15 requests", "expected": "10 allowed, 5 denied"},
                ],
            },
        ],
        "hard": [
            {
                "title": "Design a Distributed Cache",
                "description": "Design a distributed caching system that supports consistent hashing, replication, and cache invalidation. Discuss the CAP theorem trade-offs.",
                "category": "system_design",
                "test_cases": [],
            },
            {
                "title": "Implement a B-Tree",
                "description": "Implement a B-Tree data structure supporting insert, search, and delete operations. Analyze time complexity.",
                "category": "coding",
                "test_cases": [],
            },
            {
                "title": "Build a Concurrent Web Crawler",
                "description": "Design and implement a concurrent web crawler that respects robots.txt, handles rate limiting, and avoids duplicate visits. Discuss thread safety.",
                "category": "coding",
                "test_cases": [],
            },
        ],
    }

    _MCQ_TEMPLATE: list[dict] = [
        {
            "title": "Time Complexity Analysis",
            "description": "What is the time complexity of searching for an element in a balanced binary search tree?\nA) O(n)\nB) O(log n)\nC) O(1)\nD) O(n log n)",
            "category": "mcq",
            "test_cases": [{"expected": "B"}],
        },
        {
            "title": "Data Structure Selection",
            "description": "Which data structure is most efficient for implementing a priority queue?\nA) Array\nB) Linked List\nC) Heap\nD) Hash Map",
            "category": "mcq",
            "test_cases": [{"expected": "C"}],
        },
        {
            "title": "SQL Query Understanding",
            "description": "What does the SQL HAVING clause do?\nA) Filters rows before grouping\nB) Filters groups after GROUP BY\nC) Sorts the result set\nD) Joins two tables",
            "category": "mcq",
            "test_cases": [{"expected": "B"}],
        },
        {
            "title": "Design Patterns",
            "description": "Which design pattern ensures a class has only one instance and provides a global point of access?\nA) Factory\nB) Singleton\nC) Observer\nD) Strategy",
            "category": "mcq",
            "test_cases": [{"expected": "B"}],
        },
    ]

    _SQL_TEMPLATE: list[dict] = [
        {
            "title": "Employee Salary Analysis",
            "description": "Write a SQL query to find the department with the highest average salary from an employees table with columns: id, name, department, salary.",
            "category": "sql",
            "test_cases": [
                {"expected": "SELECT department, AVG(salary) FROM employees GROUP BY department ORDER BY AVG(salary) DESC LIMIT 1"}
            ],
        },
        {
            "title": "Find Duplicates",
            "description": "Write a SQL query to find all duplicate email addresses in a users table.",
            "category": "sql",
            "test_cases": [
                {"expected": "SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1"}
            ],
        },
    ]

    @classmethod
    def generate_assessments(
        cls,
        difficulty: str = "medium",
        category: str = "coding",
        count: int = 3,
    ) -> list[dict]:
        assessments = []

        if category == "mcq":
            pool = list(cls._MCQ_TEMPLATE)
            random.shuffle(pool)
            for p in pool[:count]:
                assessments.append({
                    "problem_title": p["title"],
                    "problem_description": p["description"],
                    "difficulty": difficulty,
                    "category": "mcq",
                    "test_cases": p.get("test_cases", []),
                })
        elif category == "sql":
            pool = list(cls._SQL_TEMPLATE)
            random.shuffle(pool)
            for p in pool[:count]:
                assessments.append({
                    "problem_title": p["title"],
                    "problem_description": p["description"],
                    "difficulty": difficulty,
                    "category": "sql",
                    "test_cases": p.get("test_cases", []),
                })
        else:
            pool = cls._CODING_PROBLEMS.get(difficulty, cls._CODING_PROBLEMS.get("medium", []))
            selected = random.sample(pool, min(count, len(pool)))
            for p in selected:
                assessments.append({
                    "problem_title": p["title"],
                    "problem_description": p["description"],
                    "difficulty": difficulty,
                    "category": p.get("category", "coding"),
                    "test_cases": p.get("test_cases", []),
                })

        return assessments

    @classmethod
    def evaluate_submission(cls, solution: str, test_cases: list[dict], category: str) -> dict:
        if not test_cases:
            score = 50 if solution.strip() else 0
            return {
                "is_correct": False,
                "score": score,
                "feedback": "No test cases to validate against. Partial credit based on solution presence.",
                "expected_approach": "Review the problem requirements and provide a complete solution.",
            }

        solution_lower = solution.lower().strip()
        is_correct = False
        score = 0

        if category == "mcq":
            answer_char = solution_upper = solution.strip().upper()
            if answer_char and answer_char[0] in "ABCD":
                expected = test_cases[0].get("expected", "A").strip().upper()
                is_correct = answer_char[0] == expected
                score = 100 if is_correct else 0
        elif category == "sql":
            score = cls._evaluate_sql(solution_lower)
            is_correct = score >= 70
        else:
            score = cls._evaluate_coding_solution(solution_lower, solution)
            is_correct = score >= 60

        feedback_parts = []
        if is_correct:
            feedback_parts.append("Good solution!")
        else:
            feedback_parts.append("The solution needs improvement.")

        if len(solution.split()) < 10:
            feedback_parts.append("Your solution seems incomplete. Consider adding more detail.")
        if "time complexity" in solution_lower or "o(" in solution_lower:
            score = min(score + 5, 100)
            feedback_parts.append("Good job mentioning complexity analysis!")
        else:
            feedback_parts.append("Consider mentioning time and space complexity.")

        return {
            "is_correct": is_correct,
            "score": min(score, 100),
            "feedback": " ".join(feedback_parts),
            "expected_approach": "Consider the optimal approach and edge cases.",
        }

    @staticmethod
    def _evaluate_sql(solution: str) -> int:
        score = 30
        sql_keywords = ["select", "from", "where", "group by", "having", "order by", "join"]
        found = sum(1 for kw in sql_keywords if kw in solution)
        score += min(found * 10, 40)

        if "group by" in solution:
            score += 10
        if "order by" in solution:
            score += 5
        if "having" in solution:
            score += 5
        if "count" in solution or "avg" in solution or "sum" in solution:
            score += 5

        return min(score, 100)

    @staticmethod
    def _evaluate_coding_solution(solution_lower: str, solution: str) -> int:
        score = 20

        code_indicators = ["def ", "function", "class ", "return", "if ", "for ", "while "]
        found = sum(1 for ind in code_indicators if ind in solution_lower)
        score += min(found * 10, 40)

        complexity_indicators = ["o(n", "o(1", "o(log", "time complexity", "space complexity"]
        if any(ci in solution_lower for ci in complexity_indicators):
            score += 10

        edge_cases = ["edge case", "null", "empty", "boundary", "negative", "zero"]
        if any(ec in solution_lower for ec in edge_cases):
            score += 10

        if len(solution.split("\n")) >= 3:
            score += 5

        return min(score, 100)
