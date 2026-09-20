import type { ActivityItem } from "../../types/candidate";

interface ActivityFeedProps {
  activities: ActivityItem[];
}

const typeIcons: Record<string, string> = {
  welcome: "👋",
  profile_updated: "✏️",
  resume_uploaded: "📄",
  avatar_changed: "🖼️",
  new_feature: "✨",
};

export function ActivityFeed({ activities }: ActivityFeedProps) {
  if (activities.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">
          Recent Activity
        </h3>
        <p className="text-sm text-gray-400">No recent activity</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">
        Recent Activity
      </h3>
      <div className="space-y-3">
        {activities.map((item, i) => (
          <div key={i} className="flex items-start gap-3 text-sm">
            <span className="text-lg">{typeIcons[item.type] || "📌"}</span>
            <div>
              <p className="text-gray-900 font-medium">{item.title}</p>
              <p className="text-gray-500 text-xs">{item.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
