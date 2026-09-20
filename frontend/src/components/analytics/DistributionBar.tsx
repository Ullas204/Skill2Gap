import type { DataDistribution } from "../../types/analytics";

interface Props {
  data: DataDistribution[];
  title: string;
}

const BAR_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4"];

export function DistributionBar({ data, title }: Props) {
  const total = data.reduce((s, d) => s + d.count, 0) || 1;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h4 className="text-sm font-semibold text-gray-700 mb-3">{title}</h4>
      <div className="w-full h-4 rounded-full overflow-hidden flex bg-gray-100">
        {data.map((d, i) => (
          <div
            key={d.label}
            className="h-full transition-all"
            style={{
              width: `${(d.count / total) * 100}%`,
              backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
            }}
            title={`${d.label}: ${d.count}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3 mt-2">
        {data.map((d, i) => (
          <span key={d.label} className="flex items-center gap-1 text-xs text-gray-600">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: BAR_COLORS[i % BAR_COLORS.length] }} />
            {d.label} ({d.count})
          </span>
        ))}
      </div>
    </div>
  );
}
