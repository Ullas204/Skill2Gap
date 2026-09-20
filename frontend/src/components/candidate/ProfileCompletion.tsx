import type { ProfileCompletion as ProfileCompletionType } from "../../types/candidate";

interface ProfileCompletionProps {
  data: ProfileCompletionType;
}

export function ProfileCompletion({ data }: ProfileCompletionProps) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (data.completion_percentage / 100) * circumference;

  const sectionLabels: Record<string, string> = {
    personal_info: "Personal Info",
    education: "Education",
    experience: "Experience",
    skills: "Skills",
    projects: "Projects",
    certifications: "Certifications",
    languages: "Languages",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">
        Profile Completion
      </h3>
      <div className="flex items-center gap-6">
        <div className="relative flex-shrink-0">
          <svg className="h-28 w-28 -rotate-90" viewBox="0 0 120 120">
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="8"
            />
            <circle
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke="#3b82f6"
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-500"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xl font-bold text-gray-900">
              {data.completion_percentage}%
            </span>
          </div>
        </div>
        <div className="flex-1 space-y-1.5">
          {Object.entries(data.sections).map(([key, filled]) => (
            <div key={key} className="flex items-center gap-2 text-sm">
              <div
                className={`h-2 w-2 rounded-full ${
                  filled ? "bg-green-500" : "bg-gray-300"
                }`}
              />
              <span className={filled ? "text-gray-700" : "text-gray-400"}>
                {sectionLabels[key] || key}
              </span>
            </div>
          ))}
        </div>
      </div>
      {data.recommendations.length > 0 && (
        <div className="mt-4 space-y-1">
          {data.recommendations.map((rec, i) => (
            <p key={i} className="text-xs text-amber-600">
              {rec}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
