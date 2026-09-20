import type { StatusBreakdown } from "../../types/analytics";

interface Props {
  data: StatusBreakdown[];
  title: string;
}

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-100 text-blue-800",
  under_review: "bg-yellow-100 text-yellow-800",
  shortlisted: "bg-green-100 text-green-800",
  interview_scheduled: "bg-purple-100 text-purple-800",
  rejected: "bg-red-100 text-red-800",
  offered: "bg-emerald-100 text-emerald-800",
  hired: "bg-green-100 text-green-800",
  withdrawn: "bg-gray-100 text-gray-800",
  draft: "bg-gray-100 text-gray-600",
  published: "bg-green-100 text-green-800",
  closed: "bg-red-100 text-red-600",
  archived: "bg-gray-100 text-gray-500",
};

export function StatusBreakdownChart({ data, title }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h4 className="text-sm font-semibold text-gray-700 mb-3">{title}</h4>
      <div className="space-y-2">
        {data.map((s) => (
          <div key={s.status} className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[s.status] || "bg-gray-100 text-gray-700"}`}>
              {s.status.replace(/_/g, " ")}
            </span>
            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-primary-500 rounded-full" style={{ width: `${s.percentage}%` }} />
            </div>
            <span className="text-xs text-gray-500 w-12 text-right">{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
