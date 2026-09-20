import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { recruiterJobApi } from "../../api/jobs";
import { useToast } from "../../contexts/ToastContext";
import type { JobFormData } from "../../types/jobs";

export function RecruiterJobCreate() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<JobFormData>({
    title: "",
    company: "",
    department: "",
    employment_type: "full_time",
    experience_required: "",
    education_required: "",
    required_skills: [],
    preferred_skills: [],
    location: "",
    salary_min: null,
    salary_max: null,
    salary_currency: "USD",
    description: "",
    benefits: "",
    application_deadline: null,
    status: "draft",
  });
  const [skillInput, setSkillInput] = useState("");
  const [prefSkillInput, setPrefSkillInput] = useState("");

  function addRequiredSkill() {
    if (skillInput.trim() && !form.required_skills.includes(skillInput.trim())) {
      setForm({ ...form, required_skills: [...form.required_skills, skillInput.trim()] });
    }
    setSkillInput("");
  }

  function addPreferredSkill() {
    if (prefSkillInput.trim() && !form.preferred_skills.includes(prefSkillInput.trim())) {
      setForm({ ...form, preferred_skills: [...form.preferred_skills, prefSkillInput.trim()] });
    }
    setPrefSkillInput("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const job = await recruiterJobApi.createJob(form);
      navigate(`/recruiter/jobs/${job.id}`);
    } catch {
      setError("Failed to create job. Please try again.");
      addToast("Failed to create job", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Create Job Posting</h1>
        <p className="mt-1 text-sm text-gray-500">Fill in the details to create a new job posting</p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Basic Information</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Job Title *</label>
              <input
                required
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Company *</label>
              <input
                required
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Department</label>
              <input
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.department}
                onChange={(e) => setForm({ ...form, department: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Employment Type *</label>
              <select
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.employment_type}
                onChange={(e) => setForm({ ...form, employment_type: e.target.value })}
              >
                <option value="full_time">Full Time</option>
                <option value="part_time">Part Time</option>
                <option value="contract">Contract</option>
                <option value="internship">Internship</option>
                <option value="freelance">Freelance</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Location *</label>
              <input
                required
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Experience Required</label>
              <input
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.experience_required || ""}
                onChange={(e) => setForm({ ...form, experience_required: e.target.value })}
                placeholder="e.g. 3-5 years"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Education Required</label>
              <input
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.education_required || ""}
                onChange={(e) => setForm({ ...form, education_required: e.target.value })}
                placeholder="e.g. Bachelor's in CS"
              />
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Salary</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Min Salary</label>
              <input
                type="number"
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.salary_min ?? ""}
                onChange={(e) => setForm({ ...form, salary_min: e.target.value ? Number(e.target.value) : null })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Max Salary</label>
              <input
                type="number"
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.salary_max ?? ""}
                onChange={(e) => setForm({ ...form, salary_max: e.target.value ? Number(e.target.value) : null })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Currency</label>
              <select
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.salary_currency}
                onChange={(e) => setForm({ ...form, salary_currency: e.target.value })}
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="INR">INR</option>
              </select>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Skills</h2>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">Required Skills</label>
            <div className="mt-1 flex gap-2">
              <input
                className="block flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addRequiredSkill())}
                placeholder="Type a skill and press Enter"
              />
              <button type="button" onClick={addRequiredSkill} className="rounded-lg bg-primary-600 px-3 py-2 text-sm text-white hover:bg-primary-700">
                Add
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {form.required_skills.map((s) => (
                <span key={s} className="inline-flex items-center gap-1 rounded-full bg-primary-100 px-3 py-1 text-xs font-medium text-primary-800">
                  {s}
                  <button type="button" onClick={() => setForm({ ...form, required_skills: form.required_skills.filter((x) => x !== s) })} className="text-primary-600 hover:text-primary-800">&times;</button>
                </span>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Preferred Skills</label>
            <div className="mt-1 flex gap-2">
              <input
                className="block flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={prefSkillInput}
                onChange={(e) => setPrefSkillInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addPreferredSkill())}
                placeholder="Type a skill and press Enter"
              />
              <button type="button" onClick={addPreferredSkill} className="rounded-lg bg-primary-600 px-3 py-2 text-sm text-white hover:bg-primary-700">
                Add
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {form.preferred_skills.map((s) => (
                <span key={s} className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-800">
                  {s}
                  <button type="button" onClick={() => setForm({ ...form, preferred_skills: form.preferred_skills.filter((x) => x !== s) })} className="text-gray-600 hover:text-gray-800">&times;</button>
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Description</h2>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Job Description *</label>
              <textarea
                required
                rows={6}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Benefits</label>
              <textarea
                rows={4}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.benefits || ""}
                onChange={(e) => setForm({ ...form, benefits: e.target.value })}
              />
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Additional Settings</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Application Deadline</label>
              <input
                type="date"
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.application_deadline || ""}
                onChange={(e) => setForm({ ...form, application_deadline: e.target.value || null })}
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Status</label>
              <select
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
              </select>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate("/recruiter/jobs")}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {saving ? "Creating..." : "Create Job"}
          </button>
        </div>
      </form>
    </div>
  );
}
