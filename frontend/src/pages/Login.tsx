import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";
import type { RoleName } from "../types/auth";
import { getErrorMessage } from "../utils/error";
import { validateLoginForm } from "../utils/validation";

function getDashboardPath(roles: RoleName[]): string {
  if (roles.includes("admin")) return "/admin/dashboard";
  if (roles.includes("hr")) return "/hr/dashboard";
  if (roles.includes("recruiter")) return "/recruiter/dashboard";
  return "/candidate/dashboard";
}

const roleHints = [
  { role: "admin", label: "Admin", icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z", color: "text-red-600 bg-red-50" },
  { role: "hr", label: "HR", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z", color: "text-purple-600 bg-purple-50" },
  { role: "recruiter", label: "Recruiter", icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z", color: "text-blue-600 bg-blue-50" },
  { role: "candidate", label: "Candidate", icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z", color: "text-green-600 bg-green-50" },
];

export function Login() {
  const navigate = useNavigate();
  const { login, isAuthenticated, user } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Same-app redirect target (open-redirect safe: must be a relative path).
  const searchParams = new URLSearchParams(window.location.search);
  const rawRedirect = searchParams.get("redirect") || "";
  const redirectTarget = rawRedirect.startsWith("/") && !rawRedirect.startsWith("//") ? rawRedirect : "";

  if (isAuthenticated) {
    if (redirectTarget) return <Navigate to={redirectTarget} replace />;
    return <Navigate to={getDashboardPath(user?.roles || [])} replace />;
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setErrors((prev) => ({ ...prev, [e.target.name]: "" }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError("");

    const validationErrors = validateLoginForm(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    try {
      const loggedInUser = await login({ ...form, remember_me: rememberMe });
      navigate(redirectTarget || getDashboardPath(loggedInUser.roles));
    } catch (err) {
      setServerError(getErrorMessage(err, "Login failed. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gradient-to-br from-primary-50 via-white to-primary-50">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 rounded-xl bg-primary-600 flex items-center justify-center">
            <svg className="h-7 w-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="mt-4 text-2xl font-bold text-gray-900">Welcome back</h1>
          <p className="mt-1 text-sm text-gray-500">
            Sign in to your HireCraft account
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {serverError && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-600">
              {serverError}
            </div>
          )}

          <Input
            label="Email"
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            error={errors.email}
            placeholder="you@company.com"
          />

          <Input
            label="Password"
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            error={errors.password}
            placeholder="Enter your password"
          />

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-600">Remember me</span>
            </label>
          </div>

          <Button type="submit" isLoading={isLoading} className="w-full">
            Sign in
          </Button>
        </form>

        <div className="space-y-3">
          <p className="text-center text-xs font-medium text-gray-400 uppercase tracking-wider">
            Supported roles
          </p>
          <div className="grid grid-cols-2 gap-2">
            {roleHints.map((hint) => (
              <div
                key={hint.role}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${hint.color}`}
              >
                <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={hint.icon} />
                </svg>
                {hint.label}
              </div>
            ))}
          </div>
        </div>

        <p className="text-center text-sm text-gray-500">
          Don&apos;t have an account?{" "}
          <Link to="/register" className="text-primary-600 hover:text-primary-500 font-medium">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
