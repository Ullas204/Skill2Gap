import { Navigate } from "react-router-dom";

/**
 * Backwards-compatible entry point for the legacy `/candidate/skill2job` route.
 * The feature now lives at `/skill2job/*` under Skill2JobLayout.
 */
export function Skill2JobHome() {
  return <Navigate to="/skill2job" replace />;
}

export default Skill2JobHome;