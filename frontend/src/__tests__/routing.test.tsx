import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthContext } from "../contexts/AuthContext";
import type { AuthState } from "../types/auth";
import type { Permission } from "../types/permissions";
import { RootRoute } from "../components/routing/RootRoute";
import type { RoleName, User } from "../types/auth";

function makeUser(roles: RoleName[]): User {
  return {
    id: "u-1",
    full_name: "Test User",
    email: "test@example.com",
    is_active: true,
    is_verified: true,
    roles,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

type Ctx = AuthState & {
  login: () => Promise<User>;
  register: () => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  permissions: Set<Permission>;
  can: (p: Permission) => boolean;
};

function authContext(overrides: Partial<AuthState>): Ctx {
  return {
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: false,
    login: async () => makeUser([]),
    register: async () => undefined,
    logout: async () => undefined,
    refreshAuth: async () => undefined,
    permissions: new Set<Permission>(),
    can: () => false,
    ...overrides,
  };
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

function renderRoot(ctx: Ctx) {
  return render(
    <AuthContext.Provider value={ctx}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<RootRoute />} />
          <Route path="/login" element={<div>Login page</div>} />
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("RootRoute (/)", () => {
  it("shows the landing page for unauthenticated visitors", () => {
    renderRoot(authContext({}));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Transform Recruitment/i);
    expect(screen.getAllByText("Get Started").length).toBeGreaterThan(0);
  });

  it("redirects authenticated candidates to the Career Intelligence hub", () => {
    renderRoot(
      authContext({ isAuthenticated: true, user: makeUser(["candidate"]) }),
    );
    expect(screen.getByTestId("location")).toHaveTextContent("/skill2job");
  });

  it("redirects recruiters to their dashboard", () => {
    renderRoot(authContext({ isAuthenticated: true, user: makeUser(["recruiter"]) }));
    expect(screen.getByTestId("location")).toHaveTextContent("/recruiter/dashboard");
  });

  it("redirects HR users to the HR dashboard", () => {
    renderRoot(authContext({ isAuthenticated: true, user: makeUser(["hr_manager"]) }));
    expect(screen.getByTestId("location")).toHaveTextContent("/hr/dashboard");
  });

  it("redirects admins to the admin dashboard", () => {
    renderRoot(authContext({ isAuthenticated: true, user: makeUser(["admin"]) }));
    expect(screen.getByTestId("location")).toHaveTextContent("/admin/dashboard");
  });

  it("uses privilege priority for multi-role users", () => {
    renderRoot(
      authContext({ isAuthenticated: true, user: makeUser(["candidate", "hr", "super_admin"]) }),
    );
    expect(screen.getByTestId("location")).toHaveTextContent("/admin/dashboard");
  });

  it("does not expose the landing page while auth state is loading", () => {
    renderRoot(authContext({ isLoading: true }));
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
    expect(document.querySelector(".animate-spin")).not.toBeNull();
  });
});
