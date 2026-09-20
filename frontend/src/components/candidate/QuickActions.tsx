import { useNavigate } from "react-router-dom";

interface QuickAction {
  label: string;
  path: string;
  description: string;
  icon: string;
  disabled?: boolean;
}

const actions: QuickAction[] = [
  { label: "Complete Profile", path: "/candidate/profile", description: "Fill in your details", icon: "👤" },
  { label: "Upload Resume", path: "#", description: "Coming soon", icon: "📄", disabled: true },
  { label: "Search Jobs", path: "#", description: "Coming soon", icon: "🔍", disabled: true },
  { label: "Career Insights", path: "#", description: "Coming soon", icon: "📊", disabled: true },
];

export function QuickActions() {
  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-3">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={() => !action.disabled && navigate(action.path)}
            disabled={action.disabled}
            className={`flex flex-col items-center gap-1 rounded-lg p-3 text-center text-sm transition-colors ${
              action.disabled
                ? "bg-gray-50 text-gray-300 cursor-not-allowed"
                : "bg-gray-50 text-gray-700 hover:bg-gray-100"
            }`}
          >
            <span className="text-xl">{action.icon}</span>
            <span className="font-medium">{action.label}</span>
            <span className="text-xs text-gray-400">{action.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
