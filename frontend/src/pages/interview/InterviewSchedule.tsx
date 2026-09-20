import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { interviewApi } from "../../api/interview";
import { recruiterJobApi } from "../../api/jobs";

export function InterviewSchedule() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<{ id: string; title: string }[]>([]);
  const [formData, setFormData] = useState({
    job_id: "",
    candidate_id: "",
    scheduled_at: "",
    duration_minutes: 60,
    question_count: 10,
    difficulty: "medium",
    categories: ["technical", "behavioral"],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function loadJobs() {
      try {
        const result = await recruiterJobApi.listJobs();
        setJobs(result.map((j: { id: string; title: string }) => ({ id: j.id, title: j.title })) || []);
      } catch {
      }
    }
    loadJobs();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.job_id || !formData.candidate_id || !formData.scheduled_at) {
      setError("Please fill in all required fields");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await interviewApi.scheduleInterview({
        job_id: formData.job_id,
        candidate_id: formData.candidate_id,
        scheduled_at: new Date(formData.scheduled_at).toISOString(),
        duration_minutes: formData.duration_minutes,
        question_count: formData.question_count,
        difficulty: formData.difficulty,
        categories: formData.categories,
      });
      setSuccess("Interview scheduled successfully!");
      setTimeout(() => navigate("/recruiter/interviews"), 1500);
    } catch {
      setError("Failed to schedule interview");
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = (cat: string) => {
    setFormData((prev) => ({
      ...prev,
      categories: prev.categories.includes(cat)
        ? prev.categories.filter((c) => c !== cat)
        : [...prev.categories, cat],
    }));
  };

  const allCategories = ["technical", "behavioral", "hr", "situational", "coding", "system_design", "problem_solving"];

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <button onClick={() => navigate(-1)} className="mb-2 text-sm text-primary-600 hover:text-primary-700">← Back</button>
        <h1 className="text-2xl font-bold text-gray-900">Schedule Interview</h1>
        <p className="mt-1 text-sm text-gray-500">Set up a structured interview with AI-generated questions</p>
      </div>

      {error && <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>}
      {success && <div className="rounded-lg bg-green-50 p-4 text-sm text-green-600">{success}</div>}

      <form onSubmit={handleSubmit} className="space-y-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-gray-700">Job *</label>
          <select
            value={formData.job_id}
            onChange={(e) => setFormData((prev) => ({ ...prev, job_id: e.target.value }))}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="">Select a job</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>{j.title}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Candidate ID *</label>
          <input
            type="text"
            value={formData.candidate_id}
            onChange={(e) => setFormData((prev) => ({ ...prev, candidate_id: e.target.value }))}
            placeholder="Enter candidate UUID"
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Date & Time *</label>
            <input
              type="datetime-local"
              value={formData.scheduled_at}
              onChange={(e) => setFormData((prev) => ({ ...prev, scheduled_at: e.target.value }))}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Duration (min)</label>
            <input
              type="number"
              value={formData.duration_minutes}
              onChange={(e) => setFormData((prev) => ({ ...prev, duration_minutes: parseInt(e.target.value) || 60 }))}
              min={15}
              max={180}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Difficulty</label>
            <select
              value={formData.difficulty}
              onChange={(e) => setFormData((prev) => ({ ...prev, difficulty: e.target.value }))}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Questions</label>
            <input
              type="number"
              value={formData.question_count}
              onChange={(e) => setFormData((prev) => ({ ...prev, question_count: parseInt(e.target.value) || 10 }))}
              min={1}
              max={50}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Categories</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {allCategories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => toggleCategory(cat)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  formData.categories.includes(cat)
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {cat.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {loading ? "Scheduling..." : "Schedule Interview"}
        </button>
      </form>
    </div>
  );
}
