import { Navigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { getDashboardPath } from "../utils/roleRouting";

export function Dashboard() {
  const { user } = useAuth();
  return <Navigate to={getDashboardPath(user?.roles || [])} replace />;
}
