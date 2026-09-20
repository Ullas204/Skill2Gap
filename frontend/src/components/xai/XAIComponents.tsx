import type { ConfidenceScore, FeatureImportanceItem, FactorItem } from "../../types/screening";

// ─── Score Ring ─────────────────────────────────────────────────────

export function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color =
    score >= 80 ? "#22c55e" : score >= 60 ? "#3b82f6" : score >= 40 ? "#eab308" : "#ef4444";
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth="6" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        className="font-bold"
        fill={color}
        fontSize={size * 0.25}
      >
        {score}
      </text>
    </svg>
  );
}

// ─── Confidence Indicator ───────────────────────────────────────────

export function ConfidenceIndicator({ confidence }: { confidence: ConfidenceScore }) {
  const colorMap: Record<string, string> = {
    very_high: "bg-green-100 text-green-800 border-green-200",
    high: "bg-blue-100 text-blue-800 border-blue-200",
    medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
    low: "bg-red-100 text-red-800 border-red-200",
  };
  const labelMap: Record<string, string> = {
    very_high: "Very High",
    high: "High",
    medium: "Medium",
    low: "Low",
  };
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium ${colorMap[confidence.level] || colorMap.medium}`}>
      <div className="w-2 h-2 rounded-full bg-current" />
      {labelMap[confidence.level]} ({confidence.score}%)
    </div>
  );
}

// ─── Feature Importance Bar ─────────────────────────────────────────

export function FeatureImportanceBar({ feature }: { feature: FeatureImportanceItem }) {
  const barColor =
    feature.impact === "positive"
      ? "bg-green-500"
      : feature.impact === "negative"
        ? "bg-red-500"
        : "bg-blue-500";
  const textColor =
    feature.impact === "positive"
      ? "text-green-700"
      : feature.impact === "negative"
        ? "text-red-700"
        : "text-blue-700";
  return (
    <div className="flex items-center gap-3">
      <span className="w-36 text-sm text-gray-700 shrink-0">{feature.label}</span>
      <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${feature.contribution_pct}%` }}
        />
      </div>
      <span className={`w-16 text-xs font-bold text-right ${textColor}`}>
        {feature.contribution_pct}%
      </span>
      <span className="w-8 text-xs text-gray-500 text-right">{feature.score}</span>
    </div>
  );
}

// ─── Factor List ────────────────────────────────────────────────────

export function FactorList({
  factors,
  type,
}: {
  factors: FactorItem[];
  type: "positive" | "negative";
}) {
  if (factors.length === 0) return <p className="text-sm text-gray-500">None identified</p>;
  return (
    <ul className="space-y-2">
      {factors.map((f, i) => (
        <li key={i} className="flex items-start gap-2 text-sm">
          <span className={type === "positive" ? "text-green-500 mt-0.5" : "text-red-500 mt-0.5"}>
            {type === "positive" ? "+" : "-"}
          </span>
          <div>
            <span className="font-medium text-gray-900">{f.category}</span>
            <span className="text-gray-600 ml-1">({f.score}%)</span>
            <p className="text-xs text-gray-500 mt-0.5">{f.reason}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

// ─── Stat Box ───────────────────────────────────────────────────────

export function StatBox({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

// ─── Badge ──────────────────────────────────────────────────────────

export function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${color}`}>
      {label}
    </span>
  );
}

// ─── Score Color Helpers ────────────────────────────────────────────

export function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-blue-600";
  if (score >= 40) return "text-yellow-600";
  return "text-red-600";
}

export function scoreBgColor(score: number): string {
  if (score >= 80) return "bg-green-100 text-green-800";
  if (score >= 60) return "bg-blue-100 text-blue-800";
  if (score >= 40) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

export function strengthColor(level: string): string {
  switch (level) {
    case "excellent": return "bg-green-100 text-green-800";
    case "good": return "bg-blue-100 text-blue-800";
    case "average": return "bg-yellow-100 text-yellow-800";
    default: return "bg-red-100 text-red-800";
  }
}

export function recommendationColor(rec: string): string {
  switch (rec) {
    case "strongly_recommend": return "bg-green-100 text-green-800";
    case "recommend": return "bg-blue-100 text-blue-800";
    case "consider": return "bg-yellow-100 text-yellow-800";
    default: return "bg-red-100 text-red-800";
  }
}
