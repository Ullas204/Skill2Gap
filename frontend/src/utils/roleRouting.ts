import type { RoleName } from "../types/auth";

export function getDashboardPath(roles: RoleName[]): string {
  if (roles.includes("super_admin") || roles.includes("admin")) return "/admin/dashboard";
  if (roles.includes("organization_admin")) return "/org/team";
  if (roles.includes("hr_manager") || roles.includes("hr")) return "/hr/dashboard";
  if (roles.includes("recruiter")) return "/recruiter/dashboard";
  return "/skill2job";
}

export function getNotificationPath(roles: RoleName[]): string {
  if (roles.includes("super_admin") || roles.includes("admin")) return "/admin/dashboard";
  if (roles.includes("organization_admin")) return "/org/team";
  if (roles.includes("hr_manager") || roles.includes("hr")) return "/hr/dashboard";
  if (roles.includes("recruiter")) return "/recruiter/notifications";
  return "/candidate/notifications";
}

export function getRoleBadgeColor(roles: RoleName[]): string {
  if (roles.includes("super_admin")) return "bg-red-100 text-red-700";
  if (roles.includes("admin")) return "bg-red-100 text-red-700";
  if (roles.includes("organization_admin")) return "bg-orange-100 text-orange-700";
  if (roles.includes("hr_manager") || roles.includes("hr")) return "bg-purple-100 text-purple-700";
  if (roles.includes("recruiter")) return "bg-blue-100 text-blue-700";
  return "bg-green-100 text-green-700";
}
