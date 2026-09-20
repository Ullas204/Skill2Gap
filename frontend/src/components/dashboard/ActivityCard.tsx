interface ActivityItem {
  id?: string | number;
  title: string;
  description?: string;
  time?: string;
  type?: "success" | "info" | "warning" | "error";
}

interface ActivityCardProps {
  title?: string;
  items: ActivityItem[];
  emptyMessage?: string;
}

const typeColors = {
  success: "bg-green-100 text-green-600",
  info: "bg-blue-100 text-blue-600",
  warning: "bg-amber-100 text-amber-600",
  error: "bg-red-100 text-red-600",
};

export function ActivityCard({ title = "Recent Activity", items, emptyMessage = "No activity yet" }: ActivityCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">{title}</h2>
      {items.length > 0 ? (
        <div className="space-y-3">
          {items.map((item, i) => (
            <div key={item.id ?? i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              {item.type && (
                <span className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${typeColors[item.type]}`} />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-700 truncate">{item.title}</p>
                {item.description && (
                  <p className="text-xs text-gray-500 mt-0.5 truncate">{item.description}</p>
                )}
              </div>
              {item.time && (
                <span className="text-xs text-gray-400 whitespace-nowrap shrink-0">{item.time}</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">{emptyMessage}</p>
      )}
    </div>
  );
}
