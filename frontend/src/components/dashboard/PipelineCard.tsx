import { Link } from "react-router-dom";

interface PipelineCardProps {
  title: string;
  stages: Record<string, number>;
  action?: { label: string; href: string };
  color?: "blue" | "purple" | "green";
}

const stageColors = {
  blue: ["bg-blue-100 text-blue-700", "bg-blue-50"],
  purple: ["bg-purple-100 text-purple-700", "bg-purple-50"],
  green: ["bg-green-100 text-green-700", "bg-green-50"],
};

export function PipelineCard({ title, stages, action, color = "blue" }: PipelineCardProps) {
  const entries = Object.entries(stages);
  const colors = stageColors[color];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
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
      {entries.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {entries.map(([stage, count]) => (
            <div key={stage} className={`text-center p-3 rounded-lg ${colors[1]}`}>
              <p className={`text-2xl font-bold ${colors[0].split(" ")[1]}`}>{count}</p>
              <p className="text-xs text-gray-500 mt-1 capitalize">{stage.replace(/_/g, " ")}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">No pipeline data available.</p>
      )}
    </div>
  );
}
