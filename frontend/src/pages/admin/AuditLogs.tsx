import { useEffect, useState } from "react";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { dashboardApi } from "../../api/dashboard";
import type { AuditLogItem } from "../../api/dashboard";

export function AuditLogs() {
  const { addToast } = useToast();
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi
      .getAdminAuditLogs()
      .then(setLogs)
      .catch(() => addToast("Failed to load audit logs", "error"))
      .finally(() => setLoading(false));
  }, [addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <p className="mt-1 text-sm text-gray-500">{logs.length} recent entries</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Action</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">User</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Resource</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">IP</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{log.action}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{log.user_id || "N/A"}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {log.resource_type ? `${log.resource_type}` : "N/A"}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      log.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>
                      {log.success ? "Success" : "Failed"}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{log.ip_address || "N/A"}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {logs.length === 0 && (
          <div className="p-8 text-center text-sm text-gray-500">No audit logs recorded yet.</div>
        )}
      </div>
    </div>
  );
}
