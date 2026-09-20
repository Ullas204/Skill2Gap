import { Navigate } from "react-router-dom";

import { LoadingSpinner } from "../ui/LoadingSpinner";
import { useAuth } from "../../hooks/useAuth";
import { getDashboardPath } from "../../utils/roleRouting";
import type { RoleName } from "../../types/auth";
import { LandingPage } from "../../pages/LandingPage";

/**
 * Entry route for "/".
 *
 * - While the auth state is being restored (refresh token check), render a
 *   loading screen to avoid flashing the landing page for logged-in users.
 * - Authenticated users go straight to their role dashboard using the
 *   canonical role-routing helper (multi-role aware).
 * - Unauthenticated visitors see the public landing page. The page itself
 *   makes zero API calls, so it renders instantly.
 */
export function RootRoute() {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to={getDashboardPath((user?.roles as RoleName[]) || [])} replace />;
  }

  return <LandingPage />;
}
