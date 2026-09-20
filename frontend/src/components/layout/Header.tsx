import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { notificationsApi } from "../../api/notifications";
import {
  getDashboardPath,
  getNotificationPath,
  getRoleBadgeColor,
} from "../../utils/roleRouting";

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;
    notificationsApi
      .getUnreadCount()
      .then((data) => setUnreadCount(data.count))
      .catch(() => {});
  }, [user]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="bg-white border-b border-gray-200 h-16 flex items-center px-6">
      <div className="flex-1">
        <h1
          className="text-xl font-semibold text-gray-900 cursor-pointer hover:text-primary-600 transition-colors"
          onClick={() => navigate(user ? getDashboardPath(user.roles) : "/login")}
        >
          AI Hiring Copilot
        </h1>
      </div>
      {user && (
        <div className="flex items-center gap-4">
          <div className="relative">
            <button
              onClick={() => navigate(getNotificationPath(user.roles))}
              className="text-sm text-gray-500 hover:text-gray-700 relative"
            >
              Notifications
              {unreadCount > 0 && (
                <span className="absolute -top-1.5 -right-3.5 bg-red-500 text-white text-[10px] font-bold rounded-full h-4 min-w-4 flex items-center justify-center px-1">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </button>
          </div>
          <span className="text-sm text-gray-600">
            {user.full_name}
            <span className={`ml-2 text-xs font-medium px-1.5 py-0.5 rounded-full ${getRoleBadgeColor(user.roles)}`}>
              {user.roles[0]?.charAt(0).toUpperCase() + user.roles[0]?.slice(1)}
            </span>
          </span>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}
