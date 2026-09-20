import type {
  FairnessMetricDetail,
  BiasAlert,
} from "../../types/fairness";

// --- Fairness Score Card ---

export function FairnessScoreCard({
  score,
  label = "Overall Fairness",
  size = 120,
}: {
  score: number;
  label?: string;
  size?: number;
}) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color =
    score >= 80 ? "#22c55e" : score >= 60 ? "#3b82f6" : score >= 40 ? "#eab308" : "#ef4444";
  const statusText =
    score >= 80 ? "Excellent" : score >= 60 ? "Good" : score >= 40 ? "Needs Improvement" : "Poor";

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text
          x={size / 2}
          y={size / 2 - 4}
          textAnchor="middle"
          dominantBaseline="central"
          className="font-bold"
          fill={color}
          fontSize={size * 0.22}
        >
          {score}
        </text>
        <text
          x={size / 2}
          y={size / 2 + size * 0.12}
          textAnchor="middle"
          className="text-xs"
          fill="#6b7280"
          fontSize={size * 0.09}
        >
          {statusText}
        </text>
      </svg>
      <span className="text-sm font-medium text-gray-700">{label}</span>
    </div>
  );
}

// --- Metric Status Badge ---

export function MetricStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    fair: "bg-green-100 text-green-800 border-green-200",
    good: "bg-green-100 text-green-800 border-green-200",
    excellent: "bg-green-100 text-green-800 border-green-200",
    moderate: "bg-yellow-100 text-yellow-800 border-yellow-200",
    concerning: "bg-yellow-100 text-yellow-800 border-yellow-200",
    low: "bg-yellow-100 text-yellow-800 border-yellow-200",
    biased: "bg-red-100 text-red-800 border-red-200",
    poor: "bg-red-100 text-red-800 border-red-200",
    needs_improvement: "bg-orange-100 text-orange-800 border-orange-200",
    high: "bg-red-100 text-red-800 border-red-200",
    medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status] || "bg-gray-100 text-gray-800 border-gray-200"}`}>
      {status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
    </span>
  );
}

// --- Fairness Metrics Table ---

export function FairnessMetricsTable({
  metrics,
}: {
  metrics: Record<string, FairnessMetricDetail>;
}) {
  const labels: Record<string, string> = {
    statistical_parity_difference: "Statistical Parity Difference",
    disparate_impact_ratio: "Disparate Impact Ratio",
    equal_opportunity_difference: "Equal Opportunity Difference",
    demographic_parity: "Demographic Parity",
    consistency_score: "Consistency Score",
    composite_fairness_score: "Composite Fairness Score",
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Metric</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {Object.entries(metrics).map(([key, detail]) => (
            <tr key={key} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{labels[key] || key}</td>
              <td className="px-4 py-3 text-sm text-gray-700 font-mono">{typeof detail.value === "number" ? detail.value.toFixed(4) : String(detail.value)}</td>
              <td className="px-4 py-3"><MetricStatusBadge status={detail.status} /></td>
              <td className="px-4 py-3 text-sm text-gray-500 max-w-md">{detail.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Bias Alert Panel ---

export function BiasAlertPanel({ alerts }: { alerts: BiasAlert[] }) {
  if (!alerts.length) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <p className="text-sm text-green-800">No bias alerts detected. All clear.</p>
      </div>
    );
  }

  const severityColors: Record<string, string> = {
    high: "border-red-200 bg-red-50",
    medium: "border-yellow-200 bg-yellow-50",
    low: "border-blue-200 bg-blue-50",
  };
  const severityIcons: Record<string, string> = {
    high: "\u26a0",
    medium: "\u26a0",
    low: "\u2139",
  };

  return (
    <div className="space-y-3">
      {alerts.map((alert, i) => (
        <div key={i} className={`border rounded-lg p-4 ${severityColors[alert.severity] || "border-gray-200 bg-gray-50"}`}>
          <div className="flex items-start gap-3">
            <span className="text-lg">{severityIcons[alert.severity] || "\u2139"}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-gray-900">{alert.type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</span>
                <MetricStatusBadge status={alert.severity} />
              </div>
              <p className="text-sm text-gray-700 mb-1">{alert.message}</p>
              <p className="text-xs text-gray-500">{alert.recommendation}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// --- Diversity Stat ---

export function DiversityStat({
  label,
  value,
  color = "blue",
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    green: "bg-green-50 text-green-700 border-green-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
    orange: "bg-orange-50 text-orange-700 border-orange-200",
  };
  return (
    <div className={`rounded-lg border p-3 ${colorMap[color] || colorMap.blue}`}>
      <p className="text-xs font-medium opacity-75">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

// --- Severity Count Badges ---

export function SeverityCounts({
  counts,
}: {
  counts: Record<string, number>;
}) {
  return (
    <div className="flex gap-2">
      {Object.entries(counts).map(([severity, count]) => (
        <span
          key={severity}
          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
            severity === "high"
              ? "bg-red-100 text-red-800"
              : severity === "medium"
              ? "bg-yellow-100 text-yellow-800"
              : "bg-blue-100 text-blue-800"
          }`}
        >
          {severity}: {count}
        </span>
      ))}
    </div>
  );
}

// --- Progress Bar ---

export function FairnessProgressBar({
  value,
  max = 100,
  label,
  color,
}: {
  value: number;
  max?: number;
  label?: string;
  color?: string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  const barColor = color || (pct >= 80 ? "#22c55e" : pct >= 60 ? "#3b82f6" : pct >= 40 ? "#eab308" : "#ef4444");

  return (
    <div>
      {label && (
        <div className="flex justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          <span className="text-sm font-medium text-gray-700">{Math.round(pct)}%</span>
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div className="h-2.5 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: barColor }} />
      </div>
    </div>
  );
}

// --- Issue List ---

export function IssueList({
  title,
  items,
  color = "gray",
}: {
  title: string;
  items: Array<{ term: string; suggestion: string }>;
  color?: string;
}) {
  if (!items.length) return null;
  const bgColor: Record<string, string> = {
    red: "bg-red-50 border-red-200",
    yellow: "bg-yellow-50 border-yellow-200",
    orange: "bg-orange-50 border-orange-200",
    gray: "bg-gray-50 border-gray-200",
  };
  return (
    <div className={`border rounded-lg p-4 ${bgColor[color] || bgColor.gray}`}>
      <h4 className="text-sm font-semibold text-gray-900 mb-2">{title} ({items.length})</h4>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-sm">
            <span className="font-mono font-medium text-red-700">"{item.term}"</span>
            <span className="text-gray-600 ml-2">- {item.suggestion}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
