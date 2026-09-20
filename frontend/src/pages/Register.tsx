import { Navigate, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";
import type { RoleName } from "../types/auth";
import { getErrorMessage } from "../utils/error";
import { validateRegisterForm, getPasswordStrengthIssues, getPasswordStrengthLevel } from "../utils/validation";
import { useState } from "react";

function getDashboardPath(roles: RoleName[]): string {
  if (roles.includes("super_admin") || roles.includes("admin")) return "/admin/dashboard";
  if (roles.includes("organization_admin")) return "/admin/dashboard";
  if (roles.includes("hr") || roles.includes("hr_manager")) return "/hr/dashboard";
  if (roles.includes("recruiter")) return "/recruiter/dashboard";
  return "/candidate/dashboard";
}

export function Register() {
  const navigate = useNavigate();
  const { register, isAuthenticated, user } = useAuth();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", confirm_password: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={getDashboardPath(user?.roles || [])} replace />;
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setErrors((prev) => ({ ...prev, [e.target.name]: "" }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError("");

    if (form.password !== form.confirm_password) {
      setErrors({ confirm_password: "Passwords do not match" });
      return;
    }

    const validationErrors = validateRegisterForm(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    try {
      await register({ full_name: form.full_name, email: form.email, password: form.password });
      navigate("/login");
    } catch (err) {
      setServerError(getErrorMessage(err, "Registration failed. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Create candidate account</h1>
          <p className="mt-1 text-sm text-gray-500">
            Register to explore job opportunities
          </p>
          <p className="mt-2 text-xs text-gray-400">
            Looking to join a hiring team? You'll need an invitation from your organization admin.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {serverError && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {serverError}
            </div>
          )}

          <Input
            label="Full Name"
            type="text"
            name="full_name"
            value={form.full_name}
            onChange={handleChange}
            error={errors.full_name}
            placeholder="John Doe"
          />

          <Input
            label="Email"
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            error={errors.email}
            placeholder="you@example.com"
          />

          <Input
            label="Password"
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            error={errors.password}
            placeholder="At least 8 characters"
          />

          {form.password.length > 0 && (
            <div className="space-y-1">
              <div className="flex gap-1">
                {(["weak", "fair", "strong"] as const).map((level) => {
                  const current = getPasswordStrengthLevel(form.password);
                  const levels = ["weak", "fair", "strong"];
                  const active = levels.indexOf(current) >= levels.indexOf(level);
                  return (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        active
                          ? level === "weak"
                            ? "bg-red-500"
                            : level === "fair"
                              ? "bg-yellow-500"
                              : "bg-green-500"
                          : "bg-gray-200"
                      }`}
                    />
                  );
                })}
              </div>
              <p className="text-xs text-gray-500">
                {getPasswordStrengthIssues(form.password).length === 0
                  ? "Strong password"
                  : `Needs ${getPasswordStrengthIssues(form.password).join(", ")}`}
              </p>
            </div>
          )}

          <Input
            label="Confirm Password"
            type="password"
            name="confirm_password"
            value={form.confirm_password}
            onChange={handleChange}
            error={errors.confirm_password}
            placeholder="Re-enter your password"
          />

          <Button type="submit" isLoading={isLoading} className="w-full">
            Create Candidate Account
          </Button>
        </form>

        <p className="text-center text-sm text-gray-500">
          Already have an account?{" "}
          <a href="/login" className="text-primary-600 hover:text-primary-500">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
