import { useCallback, useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { notificationsApi } from "../../api/notifications";
import type { Notification } from "../../api/notifications";

export function RecruiterNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    try {
      setNotifications(await notificationsApi.list());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkRead = async (id: string) => {
    await notificationsApi.markRead(id);
    await fetchNotifications();
  };

  const handleMarkAllRead = async () => {
    await notificationsApi.markAllRead();
    await fetchNotifications();
  };

  const handleDelete = async (id: string) => {
    await notificationsApi.delete(id);
    await fetchNotifications();
  };

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="mt-1 text-sm text-gray-500">Stay updated with applications and activity</p>
        </div>
        {notifications.length > 0 && (
          <Button variant="ghost" size="sm" onClick={handleMarkAllRead}>
            Mark all read
          </Button>
        )}
      </div>

      <div className="space-y-2">
        {notifications.length === 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <p className="text-sm text-gray-400">No notifications yet</p>
          </div>
        )}
        {notifications.map((n) => (
          <div
            key={n.id}
            className={`bg-white rounded-xl border p-4 flex items-start justify-between gap-4 ${
              n.is_read ? "border-gray-200" : "border-primary-200 bg-primary-50/30"
            }`}
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className="font-medium text-sm text-gray-900">{n.title}</p>
                {!n.is_read && (
                  <span className="h-2 w-2 rounded-full bg-primary-500" />
                )}
              </div>
              <p className="text-sm text-gray-500 mt-1">{n.message}</p>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(n.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-1">
              {!n.is_read && (
                <Button variant="ghost" size="sm" onClick={() => handleMarkRead(n.id)}>
                  Read
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => handleDelete(n.id)}>
                Delete
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
