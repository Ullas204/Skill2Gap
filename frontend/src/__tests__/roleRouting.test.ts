import { describe, expect, it } from "vitest";

import { getDashboardPath } from "../utils/roleRouting";
import type { RoleName } from "../types/auth";

describe("getDashboardPath (canonical role routing)", () => {
  it("routes admins and super admins to the admin dashboard", () => {
    expect(getDashboardPath(["admin"])).toBe("/admin/dashboard");
    expect(getDashboardPath(["super_admin"])).toBe("/admin/dashboard");
  });

  it("routes organization admins to team management", () => {
    expect(getDashboardPath(["organization_admin"])).toBe("/org/team");
  });

  it("routes HR roles to the HR dashboard", () => {
    expect(getDashboardPath(["hr"])).toBe("/hr/dashboard");
    expect(getDashboardPath(["hr_manager"])).toBe("/hr/dashboard");
  });

  it("routes recruiters to the recruiter dashboard", () => {
    expect(getDashboardPath(["recruiter"])).toBe("/recruiter/dashboard");
  });

  it("routes candidates to the Career Intelligence hub", () => {
    expect(getDashboardPath(["candidate"])).toBe("/skill2job");
  });

  it("uses privilege priority for multi-role users", () => {
    expect(getDashboardPath(["candidate", "recruiter", "admin"] as RoleName[])).toBe("/admin/dashboard");
    expect(getDashboardPath(["recruiter", "hr_manager"] as RoleName[])).toBe("/hr/dashboard");
    expect(getDashboardPath(["organization_admin", "recruiter"] as RoleName[])).toBe("/org/team");
  });

  it("falls back to the Career Intelligence hub for empty or unknown roles", () => {
    expect(getDashboardPath([])).toBe("/skill2job");
    expect(getDashboardPath(["unknown_role" as RoleName])).toBe("/skill2job");
  });
});
