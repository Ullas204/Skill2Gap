import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useAuth } from "../hooks/useAuth";
import { getErrorMessage } from "../utils/error";
import { getPasswordStrengthIssues, getPasswordStrengthLevel } from "../utils/validation";
import * as authApi from "../api/auth";

interface InvitationInfo {
  valid: boolean;
  email?: string;
  role?: string;
  organization_name?: string;
  expires_at?: string;
  status?: string;
  existing_user?: boolean;
}

const ROLE_LABELS: Record<string, string> = {
  hr_manager: "HR Manager",
  recruiter: "Recruiter",
  organization_admin: "Organization Admin",
};

function emailsMatch(a?: string, b?: string): boolean {
  return !!a && !!b && a.trim().toLowerCase() === b.trim().toLowerCase();
}

export function InviteAccept() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [invitation, setInvitation] = useState<InvitationInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState({ full_name: "", password: "", confirm_password: "" });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    async function validate() {
      if (!token) {
        setInvitation({ valid: false });
        setIsLoading(false);
        return;
      }
      try {
        const info = await authApi.validateInvitation(token);
        setInvitation(info);
      } catch {
        setInvitation({ valid: false });
      } finally {
        setIsLoading(false);
      }
    }
    validate();
  }, [token]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setFormErrors((prev) => ({ ...prev, [e.target.name]: "" }));
  };

  const handleNewUserSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError("");
    if (!token) return;

    if (form.password !== form.confirm_password) {
      setFormErrors({ confirm_password: "Passwords do not match" });
      return;
    }

    const issues = getPasswordStrengthIssues(form.password);
    if (issues.length > 0) {
      setFormErrors({ password: `Password must contain ${issues.join(", ")}` });
      return;
    }

    setIsSubmitting(true);
    try {
      await authApi.acceptInvitation({
        token,
        full_name: form.full_name,
        password: form.password,
        confirm_password: form.confirm_password,
      });
      setSuccess(true);
    } catch (err) {
      setServerError(getErrorMessage(err, "Failed to accept invitation. Please try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignedInAccept = async () => {
    if (!token) return;
    setServerError("");
    setIsSubmitting(true);
    try {
      await authApi.acceptSignedInInvitation(token);
      setSuccess(true);
    } catch (err) {
      setServerError(getErrorMessage(err, "Failed to accept invitation. Please try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="rounded-lg bg-green-50 p-6" role="status" aria-live="polite">
            <h2 className="text-lg font-semibold text-green-800">Invitation Accepted!</h2>
            <p className="mt-2 text-sm text-green-700">
              You are now a member of {invitation?.organization_name}.
            </p>
          </div>
          {!isAuthenticated && (
            <Link to="/login" className="inline-block">
              <Button>Go to Sign In</Button>
            </Link>
          )}
          {isAuthenticated && (
            <Button onClick={() => navigate("/dashboard")}>Go to Dashboard</Button>
          )}
        </div>
      </div>
    );
  }

  if (!invitation?.valid) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="rounded-lg bg-red-50 p-6" role="alert">
            <h2 className="text-lg font-semibold text-red-800">Invalid Invitation</h2>
            <p className="mt-2 text-sm text-red-700">
              This invitation link is invalid, expired, revoked, or has already been used.
            </p>
          </div>
          <Link to="/login" className="inline-block">
            <Button variant="secondary">Go to Sign In</Button>
          </Link>
        </div>
      </div>
    );
  }

  const isExistingUserFlow = invitation.existing_user === true;
  const signedInEmailMatches = isAuthenticated && emailsMatch(user?.email, invitation.email);

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Accept Invitation</h1>
          <div className="mt-3 rounded-lg bg-blue-50 p-4">
            <p className="text-sm text-blue-800">
              You've been invited to join <strong>{invitation.organization_name}</strong> as{" "}
              <strong>{ROLE_LABELS[invitation.role || ""] || invitation.role}</strong>
            </p>
            <p className="mt-1 text-xs text-blue-600">
              Invited email: {invitation.email}
            </p>
            {invitation.expires_at && (
              <p className="mt-1 text-xs text-blue-600">
                Expires: {new Date(invitation.expires_at).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>

        {serverError && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600" role="alert">
            {serverError}
          </div>
        )}

        {isExistingUserFlow ? (
          /* ── Existing-user flow ─────────────────────────────── */
          <div className="space-y-4">
            <div className="rounded-lg bg-yellow-50 p-4 text-sm text-yellow-800" role="status">
              An account already exists for this email. Sign in with{" "}
              <strong>{invitation.email}</strong> to accept this invitation.
            </div>

            {!isAuthenticated && (
              <Link
                to={`/login?redirect=${encodeURIComponent(`/invite/${token}`)}`}
                className="block"
              >
                <Button className="w-full">Sign In to Accept Invitation</Button>
              </Link>
            )}

            {isAuthenticated && !signedInEmailMatches && (
              <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700" role="alert">
                This invitation was sent to <strong>{invitation.email}</strong>, but you are
                signed in as <strong>{user?.email}</strong>. Please sign in with the invited
                email address.
              </div>
            )}

            {signedInEmailMatches && (
              <Button
                onClick={handleSignedInAccept}
                isLoading={isSubmitting}
                disabled={isSubmitting}
                className="w-full"
              >
                Accept Invitation as {user?.email}
              </Button>
            )}
          </div>
        ) : (
          /* ── New-user flow ──────────────────────────────────── */
          <form onSubmit={handleNewUserSubmit} className="space-y-4">
            <p className="text-sm text-gray-600 text-center">Create your account</p>

            <Input
              label="Email"
              type="email"
              name="email"
              value={invitation.email || ""}
              onChange={() => {}}
              error={undefined}
              placeholder={invitation.email}
              disabled
            />

            <Input
              label="Full Name"
              type="text"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              error={formErrors.full_name}
              placeholder="Your full name"
              required
            />

            <Input
              label="Password"
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              error={formErrors.password}
              placeholder="At least 8 characters"
              required
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
                            ? level === "weak" ? "bg-red-500" : level === "fair" ? "bg-yellow-500" : "bg-green-500"
                            : "bg-gray-200"
                        }`}
                      />
                    );
                  })}
                </div>
              </div>
            )}

            <Input
              label="Confirm Password"
              type="password"
              name="confirm_password"
              value={form.confirm_password}
              onChange={handleChange}
              error={formErrors.confirm_password}
              placeholder="Re-enter your password"
              required
            />

            <Button
              type="submit"
              isLoading={isSubmitting}
              disabled={isSubmitting}
              className="w-full"
            >
              Accept Invitation &amp; Create Account
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
