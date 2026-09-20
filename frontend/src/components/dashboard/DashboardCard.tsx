import { Link } from "react-router-dom";

interface DashboardCardProps {
  title: string;
  children: React.ReactNode;
  action?: { label: string; href: string };
  className?: string;
}

export function DashboardCard({ title, children, action, className = "" }: DashboardCardProps) {
  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        {action && (
          <Link
            to={action.href}
            className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
          >
            {action.label}
          </Link>
        )}
      </div>
      {children}
    </div>
  );
}
