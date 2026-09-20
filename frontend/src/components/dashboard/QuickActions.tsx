import { Link } from "react-router-dom";

interface QuickAction {
  label: string;
  href: string;
  icon?: React.ReactNode;
}

interface QuickActionsProps {
  title?: string;
  actions: QuickAction[];
}

export function QuickActions({ title = "Quick Actions", actions }: QuickActionsProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">{title}</h2>
      <div className="space-y-2">
        {actions.map((action) => (
          <Link
            key={action.href}
            to={action.href}
            className="flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm font-medium text-gray-700 transition-colors"
          >
            {action.icon && <span className="text-gray-400">{action.icon}</span>}
            {action.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
