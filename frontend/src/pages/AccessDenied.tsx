import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { usePermissions } from "../hooks/usePermissions";
import type { RoleName } from "../types/auth";
import type { Permission } from "../types/permissions";

interface AccessDeniedProps {
  requiredRoles?: RoleName[];
  requiredPermission?: Permission;
  requiredPermissions?: Permission[];
}

export function AccessDenied({ requiredRoles, requiredPermission, requiredPermissions }: AccessDeniedProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { role } = usePermissions();

  const getRedirectPath = () => {
    if (!user) return "/login";
    if (role === "admin") return "/admin/dashboard";
    if (role === "hr") return "/hr/dashboard";
    if (role === "recruiter") return "/recruiter/dashboard";
    return "/candidate/dashboard";
  };

  const getRoleLabel = (r: RoleName) => {
    const labels: Record<RoleName, string> = {
      admin: "Administrator",
      super_admin: "Super Administrator",
      organization_admin: "Organization Admin",
      hr: "HR Manager",
      hr_manager: "HR Manager",
      recruiter: "Recruiter",
      candidate: "Candidate",
    };
    return labels[r] ?? r;
  };

  const formatPermission = (p: Permission) => {
    const [domain, resource, action] = p.split(":");
    return `${action} ${resource} (${domain})`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center space-y-6 max-w-lg">
        <div className="text-6xl font-bold text-red-500">403</div>
        <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
        <p className="text-gray-500">
          You don&apos;t have the required permissions to access this page.
        </p>

        {(requiredRoles || requiredPermission || requiredPermissions) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-left">
            <h2 className="text-sm font-medium text-red-800 mb-2">Required Access:</h2>
            <ul className="text-sm text-red-700 space-y-1">
              {requiredRoles && (
                <li>
                  Role: {requiredRoles.map(getRoleLabel).join(" or ")}
                </li>
              )}
              {requiredPermission && (
                <li>Permission: {formatPermission(requiredPermission)}</li>
              )}
              {requiredPermissions && (
                <li>
                  Permissions: {requiredPermissions.map(formatPermission).join(", ")}
                </li>
              )}
            </ul>
            {user && (
              <div className="mt-3 pt-3 border-t border-red-200">
                <p className="text-xs text-red-600">
                  Your role: {role ? getRoleLabel(role) : "Unknown"} | Your roles:{" "}
                  {user.roles.map(getRoleLabel).join(", ")}
                </p>
              </div>
            )}
          </div>
        )}

        <p className="text-sm text-gray-400">
          Please contact your administrator if you believe this is an error.
        </p>

        <div className="flex gap-3 justify-center">
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Go Back
          </button>
          <button
            onClick={() => navigate(getRedirectPath())}
            className="px-4 py-2 rounded-lg bg-primary-600 text-sm font-medium text-white hover:bg-primary-700"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
