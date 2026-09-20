interface StatCardProps {
  title: string;
  value: number | string;
  icon?: React.ReactNode;
  color?: "primary" | "green" | "blue" | "purple" | "amber" | "red" | "indigo";
  trend?: { value: number; isPositive: boolean };
  subtitle?: string;
}

const colorMap = {
  primary: { bg: "bg-primary-50", text: "text-primary-600", icon: "text-primary-500" },
  green: { bg: "bg-green-50", text: "text-green-600", icon: "text-green-500" },
  blue: { bg: "bg-blue-50", text: "text-blue-600", icon: "text-blue-500" },
  purple: { bg: "bg-purple-50", text: "text-purple-600", icon: "text-purple-500" },
  amber: { bg: "bg-amber-50", text: "text-amber-600", icon: "text-amber-500" },
  red: { bg: "bg-red-50", text: "text-red-600", icon: "text-red-500" },
  indigo: { bg: "bg-indigo-50", text: "text-indigo-600", icon: "text-indigo-500" },
};

export function StatCard({ title, value, icon, color = "primary", trend, subtitle }: StatCardProps) {
  const colors = colorMap[color];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-500 truncate">{title}</p>
          <p className={`mt-1.5 text-2xl font-bold ${colors.text}`}>{value}</p>
          {subtitle && (
            <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
          )}
          {trend && (
            <div className="mt-1.5 flex items-center gap-1">
              <span className={`text-xs font-medium ${trend.isPositive ? "text-green-600" : "text-red-600"}`}>
                {trend.isPositive ? "+" : ""}{trend.value}%
              </span>
              <span className="text-xs text-gray-400">vs last month</span>
            </div>
          )}
        </div>
        {icon && (
          <div className={`${colors.bg} rounded-lg p-2.5`}>
            <div className={colors.icon}>{icon}</div>
          </div>
        )}
      </div>
    </div>
  );
}
