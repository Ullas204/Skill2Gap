import type { ChartData as ChartDataType } from "../../types/analytics";

interface Props {
  data: ChartDataType;
  height?: number;
  type?: "bar" | "line";
}

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4"];

export function ChartCard({ data, height = 200, type = "bar" }: Props) {
  const maxVal = Math.max(
    ...data.datasets.flatMap((ds) => ds.data),
    1,
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        {data.datasets.map((ds, i) => (
          <span key={ds.label} className="flex items-center gap-1 text-xs text-gray-600">
            <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: ds.color || COLORS[i % COLORS.length] }} />
            {ds.label}
          </span>
        ))}
      </div>
      <div className="flex items-end gap-1" style={{ height }}>
        {data.labels.map((label, li) => (
          <div key={label} className="flex-1 flex flex-col items-center gap-1">
            <div className="w-full flex items-end gap-px" style={{ height: height - 24 }}>
              {data.datasets.map((ds, di) => {
                const val = ds.data[li] ?? 0;
                const pct = (val / maxVal) * 100;
                const color = ds.color || COLORS[di % COLORS.length];
                if (type === "line") {
                  return (
                    <div key={ds.label} className="flex-1 relative">
                      <div
                        className="absolute bottom-0 w-full rounded-t"
                        style={{ height: `${pct}%`, backgroundColor: color, opacity: 0.8 }}
                      />
                    </div>
                  );
                }
                return (
                  <div key={ds.label} className="flex-1">
                    <div
                      className="w-full rounded-t transition-all"
                      style={{ height: `${pct}%`, backgroundColor: color }}
                      title={`${ds.label}: ${val}`}
                    />
                  </div>
                );
              })}
            </div>
            <span className="text-[10px] text-gray-500 truncate w-full text-center">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
