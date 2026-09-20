import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { assessmentApi } from "../../api/assessment";
import type { AssessmentSectionConfig } from "../../types/assessment";

const QUESTION_TYPES: { value: string; label: string }[] = [
  { value: "mcq", label: "Technical MCQ" },
  { value: "aptitude_quantitative", label: "Quantitative Aptitude" },
  { value: "aptitude_logical", label: "Logical Reasoning" },
  { value: "aptitude_verbal", label: "Verbal Ability" },
  { value: "technical_theory", label: "CS Fundamentals" },
  { value: "code_output", label: "Code Output Prediction" },
  { value: "debugging", label: "Debugging" },
  { value: "sql_mcq", label: "SQL Theory" },
  { value: "sql_query", label: "SQL Query Writing" },
  { value: "coding", label: "Coding Challenge" },
  { value: "system_design", label: "System Design" },
  { value: "scenario", label: "Scenario" },
  { value: "case_study", label: "Case Study" },
  { value: "behavioral", label: "Behavioral" },
  { value: "situational_judgment", label: "Situational Judgment" },
];

const DIFFICULTIES = ["mixed", "easy", "medium", "hard", "expert"];

interface SectionRow extends AssessmentSectionConfig {
  key: number;
}

let sectionKey = 0;
function newRow(type = "mcq"): SectionRow {
  sectionKey += 1;
  return { key: sectionKey, question_type: type, count: 5, difficulty: "mixed" };
}

export function AssessmentBuilder() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(45);
  const [passingScore, setPassingScore] = useState(60);
  const [negativeMarking, setNegativeMarking] = useState(0);
  const [allowedAttempts, setAllowedAttempts] = useState(1);
  const [adaptive, setAdaptive] = useState(false);
  const [sections, setSections] = useState<SectionRow[]>([newRow()]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [createdId, setCreatedId] = useState<string | null>(null);

  const updateRow = (key: number, patch: Partial<SectionRow>) =>
    setSections((rows) => rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  async function handleGenerate() {
    setError("");
    if (!title.trim() || title.trim().length < 3) {
      setError("Please provide a title (min 3 characters).");
      return;
    }
    setBusy(true);
    try {
      const created = await assessmentApi.generate({
        title: title.trim(),
        duration_minutes: durationMinutes,
        passing_score: passingScore,
        negative_marking: negativeMarking,
        allowed_attempts: allowedAttempts,
        adaptive,
        sections: sections.map(({ key: _key, ...cfg }) => cfg),
      });
      setCreatedId(created.id);
    } catch {
      setError("Generation failed - adjust the sections and try again.");
    } finally {
      setBusy(false);
    }
  }

  if (createdId) {
    return (
      <div className="mx-auto max-w-xl rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        <h2 className="text-xl font-bold text-gray-900">Assessment created</h2>
        <p className="mt-2 text-sm text-gray-500">
          Questions were generated, validated and published. Share the take link with candidates:
        </p>
        <code className="mt-3 block break-all rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
          /candidate/assessments/take/{createdId}
        </code>
        <div className="mt-6 flex justify-center gap-3">
          <button
            onClick={() => navigate(`/recruiter/assessments/${createdId}/analytics`)}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            View Analytics
          </button>
          <Link
            to="/recruiter/assessments"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Back to Library
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Assessment Builder</h1>
        <p className="mt-1 text-sm text-gray-500">
          Compose an assessment from AI-generated question sections
        </p>
      </div>

      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Basics</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <label className="block md:col-span-3">
            <span className="mb-1 block text-sm font-medium text-gray-700">Title</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Senior Python Engineer Screen"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Duration (minutes)</span>
            <input type="number" min={5} max={480} value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Passing score (%)</span>
            <input type="number" min={0} max={100} value={passingScore}
              onChange={(e) => setPassingScore(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Negative marking</span>
            <input type="number" min={0} max={2} step={0.25} value={negativeMarking}
              onChange={(e) => setNegativeMarking(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Allowed attempts</span>
            <input type="number" min={1} max={10} value={allowedAttempts}
              onChange={(e) => setAllowedAttempts(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </label>
          <label className="flex items-center gap-2 pt-6">
            <input type="checkbox" checked={adaptive} onChange={(e) => setAdaptive(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300" />
            <span className="text-sm font-medium text-gray-700">Adaptive difficulty</span>
          </label>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Sections</h2>
        <div className="space-y-3">
          {sections.map((row) => (
            <div key={row.key} className="flex flex-wrap items-end gap-3 rounded-lg bg-gray-50 p-3">
              <label className="min-w-[220px] grow">
                <span className="mb-1 block text-xs font-medium text-gray-600">Question type</span>
                <select value={row.question_type}
                  onChange={(e) => updateRow(row.key, { question_type: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  {QUESTION_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </label>
              <label className="w-24">
                <span className="mb-1 block text-xs font-medium text-gray-600">Count</span>
                <input type="number" min={1} max={50} value={row.count}
                  onChange={(e) => updateRow(row.key, { count: Number(e.target.value) })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </label>
              <label className="w-32">
                <span className="mb-1 block text-xs font-medium text-gray-600">Difficulty</span>
                <select value={row.difficulty || "mixed"}
                  onChange={(e) => updateRow(row.key, { difficulty: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  {DIFFICULTIES.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
              <button
                onClick={() => setSections((rows) => rows.filter((r) => r.key !== row.key))}
                disabled={sections.length === 1}
                className="rounded-lg px-3 py-2 text-sm text-red-500 hover:bg-red-50 disabled:cursor-not-allowed disabled:text-gray-300"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
        <button
          onClick={() => setSections((rows) => [...rows, newRow()])}
          className="mt-3 rounded-lg border border-dashed border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:border-primary-400 hover:text-primary-600"
        >
          + Add section
        </button>
      </div>

      <div className="flex justify-end gap-3">
        <Link
          to="/recruiter/assessments"
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </Link>
        <button
          onClick={handleGenerate}
          disabled={busy}
          className="rounded-lg bg-primary-600 px-5 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {busy ? "Generating..." : "Generate & Publish"}
        </button>
      </div>
    </div>
  );
}
