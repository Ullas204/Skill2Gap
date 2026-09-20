import { useMemo } from "react";

import { useAuth } from "./useAuth";
import {
  type Permission,
  getPermissionsForRoles,
  hasPermission as checkPermission,
  hasAnyPermission as checkAnyPermission,
  hasAllPermissions as checkAllPermissions,
} from "../types/permissions";

export function usePermissions() {
  const { user } = useAuth();

  const permissions = useMemo(() => {
    if (!user) return new Set<Permission>();
    return getPermissionsForRoles(user.roles);
  }, [user]);

  const can = useMemo(
    () => (permission: Permission) => {
      if (!user) return false;
      return checkPermission(user.roles, permission);
    },
    [user],
  );

  const canAny = useMemo(
    () => (perms: Permission[]) => {
      if (!user) return false;
      return checkAnyPermission(user.roles, perms);
    },
    [user],
  );

  const canAll = useMemo(
    () => (perms: Permission[]) => {
      if (!user) return false;
      return checkAllPermissions(user.roles, perms);
    },
    [user],
  );

  const role = useMemo(() => user?.roles?.[0] ?? null, [user]);

  return { permissions, can, canAny, canAll, role, roles: user?.roles ?? [] };
}
