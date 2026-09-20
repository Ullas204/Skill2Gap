"""Static data pools used to generate realistic synthetic demo records.

All values are generic placeholder data. No real personal information is used.
"""

from __future__ import annotations

FIRST_NAMES: list[str] = [
    "Aarav", "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia",
    "Mason", "Isabella", "Lucas", "Mia", "Aiden", "Amelia", "Rohan", "Zara",
    "Dev", "Ananya", "Kiran", "Meera", "Arjun", "Diya", "Vikram", "Saanvi",
    "Omar", "Fatima", "Diego", "Elena", "Leo", "Maya", "Kai", "Nora",
    "Felix", "Ingrid", "Sam", "Priya", "Jake", "Hannah", "Caleb", "Ruby",
]

LAST_NAMES: list[str] = [
    "Sharma", "Smith", "Johnson", "Patel", "Brown", "Garcia", "Lee", "Kumar",
    "Wang", "Davis", "Chen", "Kim", "Jones", "Rodriguez", "Singh", "Miller",
    "Gupta", "Wilson", "Anderson", "Thomas", "Iyer", "Moore", "Jackson", "Nair",
    "Martin", "Menon", "Thompson", "Das", "White", "Rao", "Harris", "Reddy",
    "Clark", "Verma", "Lewis", "Joshi", "Walker", "Agarwal", "Hall", "Kaur",
]

CITIES: list[str] = [
    "Austin, TX", "Seattle, WA", "San Francisco, CA", "New York, NY",
    "Boston, MA", "Chicago, IL", "Denver, CO", "Atlanta, GA",
    "Palo Alto, CA", "Raleigh, NC", "Phoenix, AZ", "Portland, OR",
    "Toronto, ON", "London, UK", "Berlin, DE", "Bengaluru, IN",
    "Mumbai, IN", "Hyderabad, IN", "Pune, IN", "Singapore, SG",
]

EMAIL_DOMAINS: list[str] = [
    "gmail.com", "outlook.com", "yahoo.com", "protonmail.com",
    "example.com", "mailbox.org",
]

COMPANIES: list[dict] = [
    {"name": "Nimbus Labs", "industry": "Cloud Software", "headquarters": "Austin, TX", "size_range": "201-500"},
    {"name": "DataStream AI", "industry": "Artificial Intelligence", "headquarters": "San Francisco, CA", "size_range": "51-200"},
    {"name": "Vertex Systems", "industry": "Enterprise SaaS", "headquarters": "Seattle, WA", "size_range": "501-1000"},
    {"name": "Quantia Analytics", "industry": "Data Analytics", "headquarters": "Boston, MA", "size_range": "51-200"},
    {"name": "NovaPay", "industry": "Fintech", "headquarters": "New York, NY", "size_range": "201-500"},
    {"name": "Brightline Robotics", "industry": "Robotics", "headquarters": "Palo Alto, CA", "size_range": "11-50"},
    {"name": "GreenGrid Energy", "industry": "Clean Energy", "headquarters": "Denver, CO", "size_range": "201-500"},
    {"name": "MediCore Health", "industry": "Health Tech", "headquarters": "Chicago, IL", "size_range": "501-1000"},
    {"name": "Cypher Security", "industry": "Cybersecurity", "headquarters": "Austin, TX", "size_range": "51-200"},
    {"name": "Skyline Commerce", "industry": "E-Commerce", "headquarters": "Atlanta, GA", "size_range": "1001-5000"},
]

JOB_TITLES: list[str] = [
    "Senior Software Engineer",
    "Backend Engineer",
    "Frontend Engineer",
    "Full Stack Developer",
    "Data Scientist",
    "Machine Learning Engineer",
    "DevOps Engineer",
    "Data Engineer",
    "Cloud Architect",
    "Product Manager",
    "QA Automation Engineer",
    "Security Engineer",
    "Mobile Developer",
    "Database Administrator",
    "Site Reliability Engineer",
]

DEPARTMENTS: list[str] = [
    "Engineering", "Product", "Data", "Platform", "Infrastructure",
    "Security", "Quality Assurance", "Research & Development",
]

TECHNICAL_SKILLS: list[str] = [
    "python", "javascript", "typescript", "java", "c#", "c++", "go", "rust",
    "sql", "graphql", "react", "vue", "angular", "node.js", "django",
    "fastapi", "spring boot", "docker", "kubernetes", "aws", "azure",
    "gcp", "terraform", "kafka", "redis", "postgresql", "mongodb",
    "tensorflow", "pytorch", "pandas", "spark", "hadoop", "airflow",
    "git", "linux", "nginx", "ci/cd", "jenkins", "prometheus", "grafana",
]

SOFT_SKILLS: list[str] = [
    "leadership", "communication", "problem solving", "teamwork",
    "agile", "scrum", "stakeholder management", "mentoring",
]

CERTIFICATION_TEMPLATES: list[str] = [
    "AWS Certified Solutions Architect - Associate",
    "AWS Certified Developer - Associate",
    "Google Cloud Professional Data Engineer",
    "Microsoft Certified: Azure Administrator",
    "Cisco CCNA Certification",
    "CompTIA Security+",
    "Certified ScrumMaster (CSM)",
    "PMP Certification",
    "Kubernetes CKA Certification",
    "Terraform HashiCorp Certification",
    "Professional Scrum Master (PSM I)",
    "Oracle Certified Java Programmer",
]

UNIVERSITIES: list[str] = [
    "Stanford University", "Massachusetts Institute of Technology",
    "University of California, Berkeley", "Carnegie Mellon University",
    "Georgia Institute of Technology", "University of Texas at Austin",
    "University of Washington", "University of Illinois at Urbana-Champaign",
    "Purdue University", "University of Michigan",
    "Indian Institute of Technology, Delhi", "Indian Institute of Technology, Bombay",
    "National Institute of Technology, Trichy", "Birla Institute of Technology",
    "University of Toronto", "Imperial College London",
]

DEGREES: list[str] = [
    "B.Tech in Computer Science",
    "B.S. in Computer Science",
    "B.S. in Information Technology",
    "B.E. in Electronics and Communication",
    "M.S. in Data Science",
    "M.S. in Computer Science",
    "Master of Business Administration",
    "B.Sc. in Mathematics",
    "Bachelor of Science in Computer Science",
    "M.Tech in Artificial Intelligence",
]

PROJECT_NAMES: list[str] = [
    "Real-Time Analytics Dashboard",
    "E-Commerce Recommendation Engine",
    "Distributed Task Queue",
    "CI/CD Pipeline Automation",
    "Natural Language Search",
    "Fraud Detection System",
    "Customer Churn Prediction",
    "Scalable File Storage Service",
    "Mobile Expense Tracker",
    "Serverless Notification Platform",
    "Conversational AI Assistant",
    "Data Lake Ingestion Framework",
    "Load Balancing Proxy",
    "Anomaly Detection Service",
]

RESUME_SUMMARIES: list[str] = [
    "Software engineer with a track record of building scalable, maintainable systems.",
    "Data-driven professional focused on shipping reliable products and improving processes.",
    "Engineer experienced in cloud-native development and team leadership.",
    "Passionate about clean architecture, automated testing, and developer experience.",
    "Analytical thinker who enjoys turning complex problems into simple solutions.",
]

EXPERIENCE_BULLETS: list[str] = [
    "Designed and shipped REST APIs used by millions of end users.",
    "Reduced deployment time by 60% through CI/CD automation and containerization.",
    "Led a cross-functional team of 5 engineers to deliver on schedule.",
    "Improved system reliability and observability with monitoring and alerting.",
    "Mentored junior engineers and conducted code reviews across the team.",
    "Optimized database queries, cutting average latency by 40%.",
    "Collaborated with product and design to refine technical requirements.",
    "Automated repetitive workflows, saving over 20 hours per sprint.",
]

EXPERIENCE_LEVELS: list[str] = [
    "0-2 years", "2-4 years", "3-5 years", "5-8 years", "8+ years",
]

EDUCATION_LEVELS: list[str] = [
    "Bachelor's degree required", "Bachelor's degree preferred",
    "Master's degree preferred", "Bachelor's or equivalent experience",
]

COMPANY_SUMMARIES: list[str] = [
    "We build software that powers teams and delights users.",
    "A growing company focused on data-driven products.",
    "Mission-driven team delivering reliable cloud services.",
    "We help enterprises transform with modern technology.",
]

# ── Phase 11: industry scenario pools ──────────────────────────────

# Company name pools keyed by scenario industry profile.
INDUSTRY_COMPANIES: dict[str, list[dict]] = {
    "campus": [
        {"name": "TechTern India", "industry": "IT Services", "headquarters": "Bengaluru, IN", "size_range": "1001-5000"},
        {"name": "CampusConnect Solutions", "industry": "IT Services", "headquarters": "Pune, IN", "size_range": "201-500"},
        {"name": "GradHire Systems", "industry": "Technology", "headquarters": "Hyderabad, IN", "size_range": "501-1000"},
        {"name": "Infosource Consulting", "industry": "Consulting", "headquarters": "Chennai, IN", "size_range": "1001-5000"},
        {"name": "WiproNova Digital", "industry": "IT Services", "headquarters": "Mumbai, IN", "size_range": "501-1000"},
    ],
    "startup": [
        {"name": "Zephyr AI", "industry": "Artificial Intelligence", "headquarters": "San Francisco, CA", "size_range": "11-50"},
        {"name": "Loopwire", "industry": "Developer Tools", "headquarters": "Austin, TX", "size_range": "11-50"},
        {"name": "Fernpath Health", "industry": "Health Tech", "headquarters": "Denver, CO", "size_range": "51-200"},
        {"name": "Quantic Ledger", "industry": "Fintech", "headquarters": "New York, NY", "size_range": "11-50"},
        {"name": "Orbital Delivery", "industry": "Logistics Tech", "headquarters": "Seattle, WA", "size_range": "11-50"},
    ],
    "enterprise": [
        {"name": "Vertex Global Systems", "industry": "Enterprise SaaS", "headquarters": "Seattle, WA", "size_range": "5001+"},
        {"name": "Meridian Financial Group", "industry": "Financial Services", "headquarters": "New York, NY", "size_range": "5001+"},
        {"name": "Atlas Manufacturing", "industry": "Manufacturing", "headquarters": "Chicago, IL", "size_range": "1001-5000"},
        {"name": "Continental Insurance Co", "industry": "Insurance", "headquarters": "Hartford, CT", "size_range": "5001+"},
        {"name": "Pinnacle Retail Group", "industry": "Retail", "headquarters": "Minneapolis, MN", "size_range": "5001+"},
    ],
    "it": [
        {"name": "Nimbus Labs", "industry": "Cloud Software", "headquarters": "Austin, TX", "size_range": "201-500"},
        {"name": "DataStream AI", "industry": "Artificial Intelligence", "headquarters": "San Francisco, CA", "size_range": "51-200"},
        {"name": "Vertex Systems", "industry": "Enterprise SaaS", "headquarters": "Seattle, WA", "size_range": "501-1000"},
        {"name": "Cypher Security", "industry": "Cybersecurity", "headquarters": "Austin, TX", "size_range": "51-200"},
        {"name": "Skyline Commerce", "industry": "E-Commerce", "headquarters": "Atlanta, GA", "size_range": "1001-5000"},
        {"name": "Quantia Analytics", "industry": "Data Analytics", "headquarters": "Boston, MA", "size_range": "51-200"},
    ],
    "healthcare": [
        {"name": "MediCore Health", "industry": "Health Tech", "headquarters": "Chicago, IL", "size_range": "501-1000"},
        {"name": "St. Camille Medical Center", "industry": "Healthcare", "headquarters": "Boston, MA", "size_range": "1001-5000"},
        {"name": "CareBridge Clinics", "industry": "Healthcare", "headquarters": "Phoenix, AZ", "size_range": "201-500"},
        {"name": "WellSpring Hospital Network", "industry": "Healthcare", "headquarters": "Atlanta, GA", "size_range": "5001+"},
        {"name": "BioNexus Labs", "industry": "Biotechnology", "headquarters": "San Diego, CA", "size_range": "201-500"},
    ],
    "mass": [
        {"name": "RapidStaff Workforce", "industry": "Staffing", "headquarters": "Dallas, TX", "size_range": "5001+"},
        {"name": "MetroLogix Fulfillment", "industry": "Logistics", "headquarters": "Memphis, TN", "size_range": "5001+"},
        {"name": "Sunbelt Retail Operations", "industry": "Retail", "headquarters": "Phoenix, AZ", "size_range": "5001+"},
        {"name": "PrimePath BPO", "industry": "Business Services", "headquarters": "Manila, PH", "size_range": "5001+"},
    ],
    "remote": [
        {"name": "Distributed HQ", "industry": "Remote-First Software", "headquarters": "Remote", "size_range": "51-200"},
        {"name": "Asyncline", "industry": "Collaboration Software", "headquarters": "Remote", "size_range": "51-200"},
        {"name": "NomadWorks", "industry": "Remote Platforms", "headquarters": "Remote", "size_range": "11-50"},
        {"name": "Borderless Pay", "industry": "Fintech", "headquarters": "Remote", "size_range": "51-200"},
    ],
    "finance": [
        {"name": "Sterling Capital Partners", "industry": "Investment Banking", "headquarters": "New York, NY", "size_range": "1001-5000"},
        {"name": "Meridian Financial Group", "industry": "Financial Services", "headquarters": "New York, NY", "size_range": "5001+"},
        {"name": "Quantia Risk Analytics", "industry": "FinTech Analytics", "headquarters": "Boston, MA", "size_range": "51-200"},
        {"name": "Heartland Credit Union", "industry": "Banking", "headquarters": "Columbus, OH", "size_range": "1001-5000"},
        {"name": "Aurora Asset Management", "industry": "Asset Management", "headquarters": "London, UK", "size_range": "501-1000"},
    ],
    "government": [
        {"name": "Department of Civic Services", "industry": "Government", "headquarters": "Washington, DC", "size_range": "5001+"},
        {"name": "State Revenue Authority", "industry": "Government", "headquarters": "Sacramento, CA", "size_range": "1001-5000"},
        {"name": "Municipal Works Agency", "industry": "Government", "headquarters": "Chicago, IL", "size_range": "1001-5000"},
        {"name": "Public Health Directorate", "industry": "Government", "headquarters": "Atlanta, GA", "size_range": "1001-5000"},
    ],
}

# Job title pools per scenario profile (fallback: JOB_TITLES).
INDUSTRY_JOB_TITLES: dict[str, list[str]] = {
    "campus": [
        "Software Engineer Trainee", "Associate Software Engineer",
        "Graduate Analyst", "Junior Data Analyst", "Systems Engineer Trainee",
    ],
    "startup": [
        "Founding Backend Engineer", "Full Stack Developer",
        "Product Engineer", "Growth Engineer", "ML Startup Engineer",
    ],
    "enterprise": [
        "Senior Software Engineer", "Engineering Manager",
        "Enterprise Architect", "Principal Data Scientist", "Program Manager",
    ],
    "it": [
        "Backend Engineer", "Frontend Engineer", "DevOps Engineer",
        "QA Automation Engineer", "Site Reliability Engineer",
        "Security Engineer", "Data Engineer",
    ],
    "healthcare": [
        "Registered Nurse", "Clinical Data Analyst",
        "Healthcare Software Engineer", "Medical Billing Specialist",
        "Clinical Research Coordinator", "Telehealth Support Specialist",
    ],
    "mass": [
        "Customer Support Associate", "Warehouse Operations Associate",
        "Sales Representative", "Field Technician", "Data Entry Specialist",
    ],
    "remote": [
        "Remote Full Stack Developer", "Remote Product Designer",
        "Remote Customer Success Manager", "Remote DevOps Engineer",
        "Remote Content Strategist",
    ],
    "finance": [
        "Financial Analyst", "Risk Analyst", "Compliance Officer",
        "Quantitative Developer", "Anti-Money Laundering Analyst",
        "Investment Operations Associate",
    ],
    "government": [
        "Administrative Officer", "Policy Analyst",
        "IT Systems Officer", "Public Records Clerk",
        "Program Compliance Auditor",
    ],
}

# Skill pools keyed by selectable category (Module 9 customization).
SKILL_CATEGORY_POOLS: dict[str, list[str]] = {
    "engineering": [
        "python", "javascript", "typescript", "java", "c#", "c++", "go", "rust",
        "sql", "graphql", "react", "node.js", "django", "fastapi", "spring boot",
    ],
    "data_ai": [
        "python", "sql", "tensorflow", "pytorch", "pandas", "spark", "airflow",
        "postgresql", "mongodb", "kafka", "hadoop",
    ],
    "cloud_devops": [
        "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
        "ci/cd", "jenkins", "prometheus", "grafana", "linux", "nginx",
    ],
    "healthcare": [
        "clinical documentation", "hipaa compliance", "medical coding",
        "patient care", "epic ehr", "medical terminology", "case management",
        "clinical research", "phlebotomy",
    ],
    "finance": [
        "financial modeling", "risk analysis", "gaap", "excel vba",
        "anti-money laundering", "kyc compliance", "sql", "python",
        "regulatory reporting", "derivatives",
    ],
    "government": [
        "public administration", "policy analysis", "records management",
        "procurement", "grant compliance", "civic engagement", "microsoft office",
    ],
    "support_operations": [
        "crm tools", "zendesk", "salesforce", "inventory management",
        "quality assurance", "scheduling", "data entry", "customer service",
    ],
}

# Difficulty presets used by the hiring-decision simulator (Module 6/9).
HIRING_DIFFICULTY_PRESETS: dict[str, dict] = {
    "easy": {
        "hire_threshold": 65,
        "offer_rate_for_unscored_top": 0.85,
        "rejection_rate_tail": 0.15,
        "shortlist_ratio": 0.6,
    },
    "medium": {
        "hire_threshold": 75,
        "offer_rate_for_unscored_top": 0.55,
        "rejection_rate_tail": 0.30,
        "shortlist_ratio": 0.45,
    },
    "hard": {
        "hire_threshold": 82,
        "offer_rate_for_unscored_top": 0.25,
        "rejection_rate_tail": 0.50,
        "shortlist_ratio": 0.30,
    },
}
