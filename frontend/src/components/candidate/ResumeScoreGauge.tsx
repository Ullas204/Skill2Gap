interface ResumeScoreGaugeProps {
  score: number;
  label: string;
  size?: "sm" | "md" | "lg";
}

export function ResumeScoreGauge({ score, label, size = "md" }: ResumeScoreGaugeProps) {
  const clamped = Math.min(100, Math.max(0, score));
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (clamped / 100) * circumference;

  const getColor = (s: number) => {
    if (s >= 80) return "text-green-600 stroke-green-500";
    if (s >= 60) return "text-yellow-600 stroke-yellow-500";
    return "text-red-600 stroke-red-500";
  };

  const dims = size === "sm" ? "h-24 w-24" : size === "lg" ? "h-40 w-40" : "h-32 w-32";

  return (
    <div className={`flex flex-col items-center ${dims}`}>
      <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="54" fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          className={`transition-all duration-700 ${getColor(clamped)}`}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
        <text
          x="60"
          y="60"
          textAnchor="middle"
          dy="0.35em"
          className={`fill-current text-2xl font-bold ${getColor(clamped)}`}
          transform="rotate(90, 60, 60)"
        >
          {clamped}
        </text>
      </svg>
      <p className="mt-1 text-xs font-medium text-gray-500">{label}</p>
    </div>
  );
}
