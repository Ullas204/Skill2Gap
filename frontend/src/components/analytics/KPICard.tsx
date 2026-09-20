interface Props {
  label: string;
  value: number | string;
  unit?: string;
  changePct?: number;
  icon?: string;
  color?: string;
}

export function KPICard({ label, value, unit = "", changePct, color = "primary" }: Props) {
  const colorMap: Record<string, string> = {
    primary: "bg-primary-50 text-primary-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
    red: "bg-red-50 text-red-700",
    blue: "bg-blue-50 text-blue-700",
    purple: "bg-purple-50 text-purple-700",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${colorMap[color] || colorMap.primary} px-2 py-0.5 rounded-lg`}>
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
        {unit && <span className="text-sm text-gray-400">{unit}</span>}
      </div>
      {changePct !== undefined && (
        <p className={`mt-1 text-xs ${changePct >= 0 ? "text-green-600" : "text-red-600"}`}>
          {changePct >= 0 ? "+" : ""}{changePct.toFixed(1)}% vs last period
        </p>
      )}
    </div>
  );
}
