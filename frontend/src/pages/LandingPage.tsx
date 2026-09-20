import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Award,
  BadgeCheck,
  BarChart3,
  Bot,
  BrainCircuit,
  ChevronRight,
  ClipboardList,
  Code2,
  Eye,
  FileSearch,
  GitBranch,
  Globe,
  Database,
  Layers,
  LineChart,
  Lock,
  Menu,
  MessageSquareText,
  Scale,
  Server,
  ShieldCheck,
  Sparkles,
  Target,
  UserCheck,
  Users,
  X,
  Zap,
} from "lucide-react";

// ─── Shared bits ───────────────────────────────────────────────

const NAV_LINKS = [
  { label: "Platform", href: "#platform" },
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Responsible AI", href: "#responsible-ai" },
  { label: "Technology", href: "#technology" },
];

function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="AI Hiring Copilot home">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-sm">
        <Zap className="h-5 w-5 text-white" aria-hidden="true" />
      </span>
      <span className={`text-lg font-bold tracking-tight ${dark ? "text-white" : "text-gray-900"}`}>
        AI Hiring Copilot
      </span>
    </Link>
  );
}

function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200/70 bg-white/80 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8" aria-label="Main navigation">
        <Logo />

        <ul className="hidden items-center gap-1 lg:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-3 lg:flex">
          <Link
            to="/login"
            className="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-100"
          >
            Sign In
          </Link>
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2"
          >
            Get Started
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-gray-600 hover:bg-gray-100 lg:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-6 w-6" aria-hidden="true" /> : <Menu className="h-6 w-6" aria-hidden="true" />}
        </button>
      </nav>

      {open && (
        <div className="border-t border-gray-200 bg-white lg:hidden">
          <div className="space-y-1 px-4 py-4">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="block rounded-lg px-3 py-2.5 text-base font-medium text-gray-700 hover:bg-gray-100"
              >
                {link.label}
              </a>
            ))}
            <div className="flex gap-3 pt-3">
              <Link
                to="/login"
                onClick={() => setOpen(false)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-center text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Sign In
              </Link>
              <Link
                to="/login"
                onClick={() => setOpen(false)}
                className="flex-1 rounded-lg bg-primary-600 px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-primary-700"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

// ─── Hero ──────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-primary-50/80 via-white to-white">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_40%_at_50%_0%,rgba(37,99,235,0.08),transparent)]"
        aria-hidden="true"
      />
      <div className="mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-800">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            AI-Powered Talent Intelligence &amp; Recruitment Platform
          </span>
          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
            Transform Recruitment with{" "}
            <span className="bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent">
              Responsible AI
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-gray-600">
            Screen candidates faster, understand AI decisions, reduce hiring bias, conduct intelligent
            assessments, and make data-driven hiring decisions from one unified platform.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to="/login"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary-600 px-8 py-3.5 text-base font-semibold text-white shadow-md shadow-primary-600/20 transition-all hover:bg-primary-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2 sm:w-auto"
            >
              Get Started
              <ChevronRight className="h-5 w-5" aria-hidden="true" />
            </Link>
            <a
              href="#features"
              className="inline-flex w-full items-center justify-center rounded-xl border border-gray-300 bg-white px-8 py-3.5 text-base font-semibold text-gray-700 shadow-sm transition-colors hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 sm:w-auto"
            >
              Explore Platform
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Problem → Solution ────────────────────────────────────────

const PROBLEMS = [
  "Manual resume screening",
  "Time-consuming candidate comparison",
  "Subjective evaluation",
  "Hidden AI decisions",
  "Potential hiring bias",
  "Unstructured interviews",
  "Scattered recruitment analytics",
];

const SOLUTIONS = [
  "AI Resume Screening",
  "Candidate Intelligence",
  "Explainable AI",
  "Fairness & Bias Detection",
  "AI Interview Intelligence",
  "Technical Assessments",
  "Recruitment Analytics",
  "Agentic AI HR Assistant",
];

function ProblemSolution() {
  return (
    <section id="platform" className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            From recruitment bottlenecks to intelligent hiring
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Traditional recruitment slows teams down and hides how decisions are made. Our platform replaces it end to end.
          </p>
        </div>

        <div className="mt-14 grid items-start gap-6 lg:grid-cols-[1fr_auto_1fr]">
          {/* Problem */}
          <div className="rounded-2xl border border-red-100 bg-red-50/50 p-7">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-100">
                <Target className="h-5 w-5 text-red-600" aria-hidden="true" />
              </span>
              <h3 className="text-lg font-semibold text-gray-900">The Problem</h3>
            </div>
            <ul className="mt-5 space-y-3">
              {PROBLEMS.map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm text-gray-700">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Arrow */}
          <div className="flex items-center justify-center lg:h-full lg:min-h-[280px]">
            <div className="flex h-12 w-12 rotate-90 items-center justify-center rounded-full bg-primary-600 shadow-lg shadow-primary-600/25 lg:rotate-0">
              <ChevronRight className="h-6 w-6 text-white" aria-hidden="true" />
            </div>
          </div>

          {/* Solution */}
          <div className="rounded-2xl border border-primary-100 bg-gradient-to-br from-primary-50 to-white p-7">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-100">
                <BrainCircuit className="h-5 w-5 text-primary-700" aria-hidden="true" />
              </span>
              <h3 className="text-lg font-semibold text-gray-900">The AI Solution</h3>
            </div>
            <ul className="mt-5 space-y-3">
              {SOLUTIONS.map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm font-medium text-gray-800">
                  <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary-600" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Features ──────────────────────────────────────────────────

const FEATURES = [
  {
    icon: FileSearch,
    title: "AI Resume Intelligence",
    description:
      "Automatically parse resumes and extract skills, experience, education, projects, and certifications into structured candidate profiles.",
  },
  {
    icon: Layers,
    title: "AI Candidate Ranking",
    description:
      "Match candidates against job requirements and generate explainable ranking scores for every applicant.",
  },
  {
    icon: Eye,
    title: "Explainable AI",
    description:
      "Show recruiters exactly WHY a candidate received a particular score — every decision is transparent and traceable.",
  },
  {
    icon: Scale,
    title: "Responsible AI",
    description:
      "Detect potential bias and evaluate fairness across recruitment decisions before they impact people.",
  },
  {
    icon: MessageSquareText,
    title: "AI Interview Intelligence",
    description:
      "Generate technical questions, MCQs, aptitude tests, coding challenges, SQL tasks, behavioral prompts, and system design rounds.",
  },
  {
    icon: Code2,
    title: "AI Assessments",
    description:
      "Evaluate candidates on technical skills, problem solving, coding, aptitude, and SQL with auto-scored assessments.",
  },
  {
    icon: BarChart3,
    title: "Recruitment Analytics",
    description:
      "Track hiring funnel health, recruiter performance, skill demand, hiring trends, and interview outcomes.",
  },
  {
    icon: Bot,
    title: "Agentic AI HR Assistant",
    description:
      "Use natural language to search candidates, analyze hiring data, generate reports, explain scores, and run workflows.",
  },
];

function Features() {
  return (
    <section id="features" className="bg-gray-50 py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Everything you need to hire smarter
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Eight integrated AI capabilities covering the full recruitment lifecycle.
          </p>
        </div>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature, i) => (
            <article
              key={feature.title}
              className="group relative flex flex-col rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              <span className="text-xs font-bold tracking-widest text-primary-400">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="mt-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50 transition-colors group-hover:bg-primary-100">
                <feature.icon className="h-6 w-6 text-primary-600" aria-hidden="true" />
              </span>
              <h3 className="mt-4 text-base font-semibold text-gray-900">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{feature.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── How It Works ──────────────────────────────────────────────

const STEPS = [
  {
    icon: ClipboardList,
    title: "Create Job",
    description: "Recruiter creates a job description.",
  },
  {
    icon: Users,
    title: "Candidates Apply",
    description: "Candidates upload their resumes.",
  },
  {
    icon: BrainCircuit,
    title: "AI Screening",
    description: "AI parses, analyzes, and ranks candidates.",
  },
  {
    icon: Code2,
    title: "AI Assessment & Interview",
    description: "Candidates complete technical assessments and interviews.",
  },
  {
    icon: LineChart,
    title: "Data-Driven Hiring",
    description:
      "Recruiters and HR receive AI insights, fairness reports, interview results, analytics, and recommendations.",
  },
];

function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">How it works</h2>
          <p className="mt-4 text-lg text-gray-600">
            A connected five-stage pipeline from job posting to confident hiring decisions.
          </p>
        </div>

        <ol className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
          {STEPS.map((step, i) => (
            <li key={step.title} className="relative flex flex-col rounded-2xl border border-gray-200 bg-gray-50/60 p-6">
              <div className="flex items-center justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-600 shadow-sm shadow-primary-600/25">
                  <step.icon className="h-5 w-5 text-white" aria-hidden="true" />
                </span>
                <span className="text-4xl font-extrabold text-gray-200" aria-hidden="true">
                  {i + 1}
                </span>
              </div>
              <h3 className="mt-4 text-sm font-bold uppercase tracking-wide text-primary-700">
                Step {i + 1}: {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{step.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

// ─── Role cards ────────────────────────────────────────────────

const ROLES = [
  {
    icon: UserCheck,
    accent: "bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100",
    name: "Candidate",
    description:
      "Build your profile, apply for jobs, practice interviews, complete assessments, and understand your career strengths.",
    cta: "Candidate Experience",
  },
  {
    icon: Users,
    accent: "bg-blue-50 text-blue-600 group-hover:bg-blue-100",
    name: "Recruiter",
    description: "Find, screen, rank, assess, and interview candidates efficiently.",
    cta: "Recruiter Experience",
  },
  {
    icon: ShieldCheck,
    accent: "bg-purple-50 text-purple-600 group-hover:bg-purple-100",
    name: "HR",
    description: "Monitor hiring performance, fairness, workforce analytics, and recruitment outcomes.",
    cta: "HR Intelligence",
  },
  {
    icon: Lock,
    accent: "bg-red-50 text-red-600 group-hover:bg-red-100",
    name: "Admin",
    description: "Manage users, organizations, security, audit logs, and platform operations.",
    cta: "Platform Administration",
  },
];

function RoleExperience() {
  return (
    <section className="bg-gray-50 py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            One platform, four tailored experiences
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Every role gets purpose-built tooling backed by the same responsible AI core.
          </p>
        </div>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {ROLES.map((role) => (
            <article
              key={role.name}
              className="group flex flex-col rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${role.accent}`}>
                <role.icon className="h-6 w-6" aria-hidden="true" />
              </span>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">{role.name}</h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-gray-600">{role.description}</p>
              <Link
                to="/register"
                className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-primary-700 transition-colors hover:text-primary-800"
                aria-label={`${role.cta} — create an account`}
              >
                {role.cta}
                <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Responsible AI ────────────────────────────────────────────

const TRUST_PILLARS = [
  {
    icon: Eye,
    title: "Explainability",
    description: "Every score comes with human-readable reasoning, not a black box.",
  },
  {
    icon: Scale,
    title: "Fairness",
    description: "Continuous bias detection and fairness metrics across hiring stages.",
  },
  {
    icon: GitBranch,
    title: "Auditability",
    description: "Complete audit trails for screening, scoring, and decisions.",
  },
  {
    icon: Globe,
    title: "Transparency",
    description: "Candidates and recruiters see how evaluations are performed.",
  },
  {
    icon: UserCheck,
    title: "Human Oversight",
    description: "Recommendations, never verdicts — people stay in control.",
  },
];

function ResponsibleAI() {
  return (
    <section id="responsible-ai" className="relative overflow-hidden bg-gray-900 py-20 sm:py-24">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(50%_50%_at_50%_0%,rgba(59,130,246,0.15),transparent)]"
        aria-hidden="true"
      />
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary-400/30 bg-primary-400/10 px-3.5 py-1.5 text-xs font-semibold text-primary-300">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            Responsible AI at the Core
          </span>
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-white sm:text-4xl">
            AI automation with human judgment
          </h2>
          <p className="mt-5 text-lg leading-relaxed text-gray-300">
            The platform combines <strong className="font-semibold text-white">AI Automation</strong> +{" "}
            <strong className="font-semibold text-white">Explainable AI</strong> +{" "}
            <strong className="font-semibold text-white">Fairness</strong> +{" "}
            <strong className="font-semibold text-white">Human Decision Making</strong>.
          </p>
          <blockquote className="mx-auto mt-8 max-w-2xl rounded-2xl border border-gray-700/60 bg-gray-800/50 px-6 py-5 backdrop-blur">
            <p className="text-base font-medium italic text-gray-100 sm:text-lg">
              “AI assists hiring decisions. Humans remain responsible for final hiring decisions.”
            </p>
          </blockquote>
        </div>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
          {TRUST_PILLARS.map((pillar) => (
            <div key={pillar.title} className="rounded-2xl border border-gray-700/60 bg-gray-800/40 p-5 backdrop-blur">
              <pillar.icon className="h-6 w-6 text-primary-400" aria-hidden="true" />
              <h3 className="mt-3 text-sm font-semibold text-white">{pillar.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-gray-400">{pillar.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Technology ────────────────────────────────────────────────

const STACK = [
  {
    icon: Globe,
    category: "Frontend",
    items: ["React", "TypeScript", "Tailwind CSS"],
  },
  {
    icon: Server,
    category: "Backend",
    items: ["FastAPI", "Python", "SQLAlchemy"],
  },
  {
    icon: Database,
    category: "Database",
    items: ["PostgreSQL"],
  },
  {
    icon: BrainCircuit,
    category: "AI & ML",
    items: ["Sentence Transformers", "FAISS", "SHAP", "LIME", "LLM", "RAG", "LangGraph"],
  },
  {
    icon: Layers,
    category: "Infrastructure",
    items: ["Docker", "Redis", "Celery"],
  },
];

function Technology() {
  return (
    <section id="technology" className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Built on a Modern AI Engineering Stack
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Production-grade technology chosen for reliability, explainability, and scale.
          </p>
        </div>

        <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {STACK.map((layer) => (
            <div key={layer.category} className="rounded-2xl border border-gray-200 bg-gray-50/60 p-6">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-900">
                  <layer.icon className="h-5 w-5 text-white" aria-hidden="true" />
                </span>
                <h3 className="text-sm font-bold uppercase tracking-wide text-gray-900">{layer.category}</h3>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {layer.items.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-700"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Platform statistics (capability-based, no fabricated data) ──

const PLATFORM_STATS = [
  { icon: BrainCircuit, value: "8", label: "Integrated AI Capabilities" },
  { icon: ClipboardList, value: "5", label: "Connected Hiring Stages" },
  { icon: Users, value: "4", label: "Purpose-Built Role Experiences" },
  { icon: ShieldCheck, value: "100%", label: "Human Oversight on Decisions" },
];

function Stats() {
  return (
    <section className="border-y border-gray-200 bg-gray-50 py-14">
      <dl className="mx-auto grid max-w-7xl grid-cols-2 gap-8 px-4 sm:px-6 lg:grid-cols-4 lg:px-8">
        {PLATFORM_STATS.map((stat) => (
          <div key={stat.label} className="flex flex-col items-center text-center">
            <dt className="order-2 mt-2 flex items-center gap-1.5 text-sm font-medium text-gray-600">
              <stat.icon className="h-4 w-4 text-primary-500" aria-hidden="true" />
              {stat.label}
            </dt>
            <dd className="order-1 text-4xl font-extrabold tracking-tight text-gray-900">{stat.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// ─── Final CTA ─────────────────────────────────────────────────

function FinalCTA() {
  return (
    <section className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary-700 via-primary-800 to-gray-900 px-6 py-16 text-center shadow-xl sm:px-16">
          <div
            className="pointer-events-none absolute inset-0 opacity-40 [background-image:radial-gradient(rgba(255,255,255,0.12)_1px,transparent_1px)] [background-size:22px_22px]"
            aria-hidden="true"
          />
          <div className="relative mx-auto max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Build a Smarter, Fairer Hiring Process
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-primary-100">
              Bring candidate intelligence, responsible AI, assessments, interviews, and recruitment
              analytics together in one platform.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link
                to="/login"
                className="inline-flex w-full items-center justify-center rounded-xl bg-white px-8 py-3.5 text-base font-semibold text-primary-800 shadow-md transition-colors hover:bg-primary-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-800 sm:w-auto"
              >
                Get Started
              </Link>
              <Link
                to="/register"
                className="inline-flex w-full items-center justify-center rounded-xl border border-white/40 bg-white/10 px-8 py-3.5 text-base font-semibold text-white backdrop-blur transition-colors hover:bg-white/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-800 sm:w-auto"
              >
                Create Account
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Footer ────────────────────────────────────────────────────

const FOOTER_SECTIONS = [
  {
    heading: "Platform",
    links: [
      { label: "Candidate Intelligence", href: "#platform" },
      { label: "AI Screening", href: "#features" },
      { label: "Assessments", href: "#features" },
      { label: "Interviews", href: "#how-it-works" },
      { label: "Analytics", href: "#features" },
    ],
  },
  {
    heading: "Responsible AI",
    links: [
      { label: "Explainability", href: "#responsible-ai" },
      { label: "Fairness", href: "#responsible-ai" },
      { label: "Transparency", href: "#responsible-ai" },
      { label: "Human Oversight", href: "#responsible-ai" },
    ],
  },
  {
    heading: "Access",
    links: [
      { label: "Candidate", href: "/login" },
      { label: "Recruiter", href: "/login" },
      { label: "HR", href: "/login" },
      { label: "Admin", href: "/login" },
    ],
  },
];

function Footer() {
  return (
    <footer className="bg-gray-900" role="contentinfo">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[1.5fr_repeat(3,1fr)]">
          <div>
            <Logo dark />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-gray-400">
              AI-assisted hiring with transparency and human oversight.
            </p>
            <div className="mt-5 flex items-center gap-2 text-xs text-gray-500">
              <Lock className="h-3.5 w-3.5" aria-hidden="true" />
              Enterprise-grade security &amp; audit logging
            </div>
          </div>

          {FOOTER_SECTIONS.map((section) => (
            <nav key={section.heading} aria-label={`Footer — ${section.heading}`}>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-white">{section.heading}</h3>
              <ul className="mt-4 space-y-2.5">
                {section.links.map((link) =>
                  link.href.startsWith("/") ? (
                    <li key={link.label}>
                      <Link to={link.href} className="text-sm text-gray-400 transition-colors hover:text-white">
                        {link.label}
                      </Link>
                    </li>
                  ) : (
                    <li key={link.label}>
                      <a href={link.href} className="text-sm text-gray-400 transition-colors hover:text-white">
                        {link.label}
                      </a>
                    </li>
                  ),
                )}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-gray-800 pt-8 sm:flex-row">
          <p className="text-sm text-gray-500">© {new Date().getFullYear()} AI Hiring Copilot. All rights reserved.</p>
          <p className="flex items-center gap-1.5 text-xs text-gray-500">
            <Award className="h-3.5 w-3.5" aria-hidden="true" />
            Responsible AI by design
          </p>
        </div>
      </div>
    </footer>
  );
}

// ─── Page ──────────────────────────────────────────────────────

export function LandingPage() {
  // Smooth-scroll for in-page anchors without global CSS side effects.
  useEffect(() => {
    document.documentElement.style.scrollBehavior = "smooth";
    return () => {
      document.documentElement.style.scrollBehavior = "";
    };
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <main>
        <Hero />
        <ProblemSolution />
        <Features />
        <HowItWorks />
        <RoleExperience />
        <ResponsibleAI />
        <Technology />
        <Stats />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
