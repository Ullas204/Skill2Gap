import { useEffect, useState } from "react";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { CandidateIntelligence as Intel } from "../../types/candidate";

const LEVEL_LABELS: Record<string, string> = {
  not_specified: "Not specified",
  high_school: "High School",
  associate: "Associate Degree",
  bachelor: "Bachelor's Degree",
  master: "Master's Degree",
  doctorate: "Doctorate",
};

export function CandidateIntelligence() {
  const [data, setData] = useState<Intel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const result = await candidateApi.getIntelligence();
        setData(result);
      } catch {
        setError("Failed to load intelligence data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>;
  if (!data) return null;

  const strengthColor =
    data.profile_strength >= 80
      ? "text-green-600"
      : data.profile_strength >= 50
        ? "text-amber-500"
        : "text-red-500";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Candidate Intelligence</h1>
        <p className="mt-1 text-sm text-gray-500">
          AI-powered insights derived from your profile and resumes
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatBox label="Total Experience" value={`${data.total_experience_years} yrs`} sub={`${data.total_experience_months} months`} color="blue" />
        <StatBox label="Highest Qualification" value={data.highest_qualification || "N/A"} sub={LEVEL_LABELS[data.education_level] || data.education_level} color="green" />
        <StatBox label="Projects" value={String(data.project_count)} sub="total" color="purple" />
        <StatBox label="Certifications" value={String(data.certification_count)} sub="earned" color="amber" />
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Profile Strength</h2>
          <span className={`text-3xl font-bold ${strengthColor}`}>{data.profile_strength}%</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              data.profile_strength >= 80 ? "bg-green-500" : data.profile_strength >= 50 ? "bg-amber-500" : "bg-red-500"
            }`}
            style={{ width: `${data.profile_strength}%` }}
          />
        </div>
      </div>

      {Object.keys(data.skills_by_category).length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Skills by Category</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(data.skills_by_category).map(([category, skills]) => (
              <div key={category} className="rounded-md bg-gray-50 p-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {category.replace(/_/g, " ")}
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary-700"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.recommendations.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
          <h2 className="mb-3 text-lg font-semibold text-amber-900">Recommendations</h2>
          <ul className="space-y-2">
            {data.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-800">
                <span className="mt-0.5 text-amber-500">&bull;</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.missing_sections.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Missing Sections</h2>
          <div className="flex flex-wrap gap-2">
            {data.missing_sections.map((section) => (
              <span
                key={section}
                className="rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700"
              >
                {section.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  const colorMap: Record<string, string> = {
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    green: "border-green-200 bg-green-50 text-green-700",
    purple: "border-purple-200 bg-purple-50 text-purple-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
  };
  return (
    <div className={`rounded-lg border p-4 ${colorMap[color] || colorMap.blue}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 text-xl font-bold">{value}</p>
      <p className="text-xs opacity-70">{sub}</p>
    </div>
  );
}
