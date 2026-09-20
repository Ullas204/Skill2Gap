interface StatCardProps {
  label: string;
  value: string | number;
  icon?: string;
  color?: string;
}

const colorMap: Record<string, string> = {
  blue: "bg-blue-50 text-blue-700 border-blue-200",
  green: "bg-green-50 text-green-700 border-green-200",
  purple: "bg-purple-50 text-purple-700 border-purple-200",
  amber: "bg-amber-50 text-amber-700 border-amber-200",
  indigo: "bg-indigo-50 text-indigo-700 border-indigo-200",
  rose: "bg-rose-50 text-rose-700 border-rose-200",
};

export function StatCard({ label, value, color = "blue" }: StatCardProps) {
  return (
    <div
      className={`rounded-xl p-4 border ${colorMap[color] || colorMap.blue}`}
    >
      <p className="text-sm font-medium opacity-80">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
