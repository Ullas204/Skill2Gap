interface UserListItem {
  id: string;
  name: string;
  subtitle?: string;
  score?: number;
  badge?: { label: string; color: string };
}

interface UserListCardProps {
  title: string;
  users: UserListItem[];
  emptyMessage?: string;
  action?: { label: string; href: string };
}

export function UserListCard({ title, users, emptyMessage = "No data available", action }: UserListCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        {action && (
          <a href={action.href} className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors">
            {action.label}
          </a>
        )}
      </div>
      {users.length > 0 ? (
        <div className="space-y-2">
          {users.map((user) => (
            <div key={user.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-700 truncate">{user.name}</p>
                {user.subtitle && (
                  <p className="text-xs text-gray-500 truncate">{user.subtitle}</p>
                )}
              </div>
              {user.score !== undefined && (
                <span className={`text-sm font-bold px-2.5 py-0.5 rounded-full shrink-0 ml-3 ${
                  user.score >= 80 ? "bg-green-100 text-green-700" :
                  user.score >= 60 ? "bg-blue-100 text-blue-700" :
                  "bg-yellow-100 text-yellow-700"
                }`}>
                  {user.score}%
                </span>
              )}
              {user.badge && (
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ml-3 ${user.badge.color}`}>
                  {user.badge.label}
                </span>
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
