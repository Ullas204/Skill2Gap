"""Tests for Resume Analysis Engine."""

from app.services.candidate.resume_analysis import ResumeAnalysisEngine


class TestAnalyze:
    def test_full_parsed_data(self):
        data = {
            "raw_text": "Experienced software engineer with 5+ years. Led team of 10 developers. "
                        "Increased revenue by 20%. Implemented CI/CD pipeline using Docker and Kubernetes. "
                        "Email: test@example.com Phone: +1234567890 LinkedIn: linkedin.com/in/test",
            "personal_info": {"name": "Test", "email": "test@example.com"},
            "education": [{"degree": "B.Tech", "institution": "MIT"}],
            "experience": [{"title": "Engineer", "company": "Acme", "start_date": "2020-01"}],
            "skills": [{"name": "Python"}, {"name": "Docker"}, {"name": "Kubernetes"}],
            "projects": [{"name": "Project A", "description": "Built with React"}],
            "certifications": [{"name": "AWS Certified"}],
            "languages": [{"language": "English"}],
        }
        result = ResumeAnalysisEngine.analyze(data)
        assert result["quality_score"] == 100
        assert result["completeness_score"] >= 60
        assert result["readability_score"] >= 50
        assert result["professionalism_score"] >= 50
        assert result["keyword_optimization_score"] >= 30
        assert result["ats_score"] >= 30
        assert result["missing_sections"] == []
        assert len(result["strengths"]) > 0
        assert len(result["recommendations"]) > 0
        assert result["skill_analysis"]["total_skills"] == 3
        assert result["section_scores"]["experience"] == 30
        assert result["section_scores"]["education"] == 15

    def test_empty_parsed_data(self):
        data = {"raw_text": "", "personal_info": {}, "education": [], "experience": [], "skills": [], "projects": [], "certifications": [], "languages": []}
        result = ResumeAnalysisEngine.analyze(data)
        assert result["quality_score"] == 0
        assert result["completeness_score"] == 0
        assert result["readability_score"] == 0
        assert result["professionalism_score"] == 0
        assert result["keyword_optimization_score"] == 0
        assert result["ats_score"] == 0
        assert len(result["missing_sections"]) == 5
        assert len(result["weaknesses"]) > 0
        assert result["skill_analysis"]["total_skills"] == 0

    def test_partial_data(self):
        data = {
            "raw_text": "Developer with skills in Python and JavaScript. test@example.com",
            "personal_info": {"email": "test@example.com"},
            "education": [],
            "experience": [{"title": "Dev", "company": "Co"}],
            "skills": [{"name": "Python"}, {"name": "JavaScript"}],
            "projects": [],
            "certifications": [],
            "languages": [],
        }
        result = ResumeAnalysisEngine.analyze(data)
        assert 20 <= result["quality_score"] <= 60
        assert "education" in result["missing_sections"]
        assert "projects" in result["missing_sections"]


class TestCompletenessScore:
    def test_full_completeness(self):
        data = {
            "personal_info": {"name": "T", "email": "t@t.com", "phone": "123", "location": "NY"},
            "education": [{"d": "a"}, {"d": "b"}],
            "experience": [{"t": "a"}, {"t": "b"}, {"t": "c"}],
            "skills": [{"n": "a"}, {"n": "b"}, {"n": "c"}, {"n": "d"}, {"n": "e"}],
            "projects": [{"n": "a"}],
            "certifications": [{"n": "a"}],
        }
        score = ResumeAnalysisEngine._calculate_completeness_score(data)
        assert score > 50

    def test_empty_completeness(self):
        data = {"personal_info": {}, "education": [], "experience": [], "skills": [], "projects": [], "certifications": []}
        score = ResumeAnalysisEngine._calculate_completeness_score(data)
        assert score == 0


class TestReadabilityScore:
    def test_good_readability(self):
        text = ("I led a team of engineers to deliver a major platform upgrade. "
                "The project resulted in 40% improvement in system performance. "
                "• Developed REST APIs using FastAPI\n"
                "• Implemented CI/CD pipeline\n"
                "• Managed Kubernetes clusters\n\n"
                "Previous role involved full-stack development with React.")
        score = ResumeAnalysisEngine._calculate_readability_score(text)
        assert score >= 70

    def test_poor_readability(self):
        text = "short"
        score = ResumeAnalysisEngine._calculate_readability_score(text)
        assert score < 50

    def test_empty_readability(self):
        assert ResumeAnalysisEngine._calculate_readability_score("") == 0


class TestProfessionalismScore:
    def test_high_professionalism(self):
        text = ("I achieved 30% revenue growth. Led a team of 15. "
                "Managed $2M budget. Improved efficiency by 40%. "
                "test@example.com linkedin.com/in/test github.com/test "
                "Developed, implemented, optimized, delivered, launched.")
        result = ResumeAnalysisEngine._calculate_professionalism_score(text, {"personal_info": True})
        assert result >= 60

    def test_low_professionalism(self):
        text = "did some work at a company"
        result = ResumeAnalysisEngine._calculate_professionalism_score(text, {})
        assert result < 50


class TestKeywordOptimizationScore:
    def test_with_keywords(self):
        text = "achieved improved implemented developed designed led managed created delivered launched"
        skills = ["python", "docker", "kubernetes"]
        score = ResumeAnalysisEngine._calculate_keyword_optimization_score(text, skills)
        assert score > 30

    def test_no_keywords(self):
        assert ResumeAnalysisEngine._calculate_keyword_optimization_score("hello world", []) == 30


class TestATSScore:
    def test_good_ats(self):
        text = ("Experienced developer. achieved improved implemented designed led managed "
                "test@example.com +1234567890 "
                "experience education skills summary")
        data = {"experience": [{"t": "a"}], "education": [{"d": "b"}], "skills": [{"n": "c"}], "projects": [{"n": "d"}]}
        score = ResumeAnalysisEngine._calculate_ats_score(text, data)
        assert score >= 40

    def test_poor_ats(self):
        assert ResumeAnalysisEngine._calculate_ats_score("", {}) == 0


class TestSkillAnalysis:
    def test_with_skills(self):
        skills = [{"name": "Python"}, {"name": "Docker"}, {"name": "Python"}, {"name": "React"}]
        text = "Python developer with Docker and React experience"
        result = ResumeAnalysisEngine._analyze_skills(skills, text)
        assert result["total_skills"] == 3
        assert "Python" in result["duplicates"]
        assert "categorized" in result
        assert result["total_skills"] > 0

    def test_no_skills(self):
        result = ResumeAnalysisEngine._analyze_skills([], "")
        assert result["total_skills"] == 0
        assert result["duplicates"] == []


class TestFormatting:
    def test_good_formatting(self):
        text = "\n".join(["line"] * 40) + "\ntest@example.com\nlinkedin\ngithub"
        issues = ResumeAnalysisEngine._check_formatting(text)
        assert len(issues) == 0

    def test_short_resume(self):
        issues = ResumeAnalysisEngine._check_formatting("short text")
        assert len(issues) > 0


class TestKeywordAnalysis:
    def test_found_keywords(self):
        text = "achieved improved implemented developed"
        result = ResumeAnalysisEngine._analyze_keywords(text, {})
        assert result["matched_action_keywords"] >= 4
        assert "keyword_density" in result
        assert result["keyword_density"]["achieved"] == 1


class TestStrengthsWeaknesses:
    def test_strengths_with_full_data(self):
        sections = {"personal_info": True, "education": True, "experience": True, "skills": True, "projects": True}
        strengths = ResumeAnalysisEngine._identify_strengths(sections, 85, 75, 80, 75, {"total_skills": 12, "duplicates": []})
        assert len(strengths) >= 3

    def test_weaknesses_with_missing_sections(self):
        weaknesses = ResumeAnalysisEngine._identify_weaknesses(
            ["education", "projects"], 40, 30, 30, 30, ["Resume content appears too short"], {"duplicates": ["Python"], "missing_essential": ["git"], "total_skills": 2}
        )
        assert len(weaknesses) >= 3


class TestRecommendations:
    def test_generates_recommendations(self):
        recs = ResumeAnalysisEngine._generate_recommendations(
            sections={"experience": False, "skills": False, "projects": False, "education": False, "certifications": False, "languages": False, "personal_info": True},
            missing_sections=["experience", "skills", "projects", "education"],
            quality_score=10,
            readability_score=30,
            professionalism_score=20,
            keyword_optimization_score=20,
            ats_score=20,
            formatting_issues=["Resume is very short"],
            skill_analysis={"missing_essential": ["git"], "duplicates": [], "suggestions": ["docker"]},
            raw_text="hello",
        )
        assert len(recs) >= 5
