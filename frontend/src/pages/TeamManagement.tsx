import { useCallback, useEffect, useState } from "react";

import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { LoadingSpinner } from "../components/ui/LoadingSpinner";
import { useAuth } from "../hooks/useAuth";
import type { Organization, OrganizationMembership, Invitation } from "../types/auth";
import * as authApi from "../api/auth";

const ROLE_LABELS: Record<string, string> = {
  organization_admin: "Org Admin",
  hr_manager: "HR Manager",
  recruiter: "Recruiter",
  candidate: "Candidate",
};

const ROLE_COLORS: Record<string, string> = {
  organization_admin: "bg-purple-100 text-purple-800",
  hr_manager: "bg-blue-100 text-blue-800",
  recruiter: "bg-green-100 text-green-800",
  candidate: "bg-gray-100 text-gray-800",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  suspended: "bg-yellow-100 text-yellow-800",
  revoked: "bg-red-100 text-red-800",
  invited: "bg-blue-100 text-blue-800",
  pending: "bg-yellow-100 text-yellow-800",
};

export function TeamManagement() {
  const { user } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMembership[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "recruiter" });
  const [inviteError, setInviteError] = useState("");
  const [inviteSuccess, setInviteSuccess] = useState("");
  const [isInviting, setIsInviting] = useState(false);
  const [orgForm, setOrgForm] = useState({ name: "", slug: "" });
  const [orgError, setOrgError] = useState("");
  const [isCreatingOrg, setIsCreatingOrg] = useState(false);

  const loadData = useCallback(async (orgId: string) => {
    try {
      const [membersResp, invitationsResp] = await Promise.all([
        authApi.getOrgMembers(orgId),
        authApi.getOrgInvitations(orgId),
      ]);
      setMembers(membersResp.items);
      setInvitations(invitationsResp.items);
    } catch {
      console.error("Failed to load team data");
    }
  }, []);

  useEffect(() => {
    async function init() {
      try {
        const orgs = await authApi.getMyOrganizations();
        setOrganizations(orgs);
        if (orgs.length > 0) {
          setSelectedOrg(orgs[0]);
          await loadData(orgs[0].id);
        }
      } catch {
        console.error("Failed to load organizations");
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, [loadData]);

  const handleOrgChange = async (orgId: string) => {
    const org = organizations.find((o) => o.id === orgId);
    if (org) {
      setSelectedOrg(org);
      await loadData(org.id);
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setOrgError("");
    setIsCreatingOrg(true);
    try {
      const newOrg = await authApi.createOrganization({ name: orgForm.name, slug: orgForm.slug });
      setOrganizations([newOrg]);
      setSelectedOrg(newOrg);
      setOrgForm({ name: "", slug: "" });
      await loadData(newOrg.id);
    } catch (err: any) {
      setOrgError(err?.response?.data?.detail || "Failed to create organization");
    } finally {
      setIsCreatingOrg(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteError("");
    setInviteSuccess("");
    if (!selectedOrg) return;

    setIsInviting(true);
    try {
      const invitation = await authApi.inviteMember(selectedOrg.id, inviteForm.email, inviteForm.role);
      if (invitation.email_status === "skipped" || invitation.email_status === "error") {
        setInviteError(
          `Invitation created, but the email could not be delivered to ${inviteForm.email}. Check SMTP settings in backend/.env and restart the backend.`
        );
      } else {
        setInviteSuccess(`Invitation sent to ${inviteForm.email}`);
      }
      setInviteForm({ email: "", role: "recruiter" });
      await loadData(selectedOrg.id);
    } catch (err: any) {
      setInviteError(err?.response?.data?.detail || "Failed to send invitation");
    } finally {
      setIsInviting(false);
    }
  };

  const handleRevokeInvitation = async (invitationId: string) => {
    if (!selectedOrg) return;
    try {
      await authApi.revokeInvitation(selectedOrg.id, invitationId);
      await loadData(selectedOrg.id);
    } catch {
      console.error("Failed to revoke invitation");
    }
  };

  const handleResendInvitation = async (invitationId: string) => {
    if (!selectedOrg) return;
    try {
      await authApi.resendInvitation(selectedOrg.id, invitationId);
      await loadData(selectedOrg.id);
    } catch {
      console.error("Failed to resend invitation");
    }
  };

  const handleToggleMemberStatus = async (membershipId: string, currentStatus: string) => {
    if (!selectedOrg) return;
    const newStatus = currentStatus === "active" ? "suspended" : "active";
    try {
      await authApi.updateMemberStatus(selectedOrg.id, membershipId, newStatus);
      await loadData(selectedOrg.id);
    } catch {
      console.error("Failed to update member status");
    }
  };

  const isOrgAdmin = user?.roles?.includes("organization_admin") || user?.roles?.includes("super_admin") || user?.roles?.includes("admin");

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!isOrgAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900">Access Denied</h2>
          <p className="mt-2 text-gray-500">You need organization admin privileges to manage teams.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Team Management</h1>
        <p className="mt-1 text-sm text-gray-500">Manage your organization's team members and invitations.</p>
      </div>

      {organizations.length > 1 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Organization</label>
          <select
            value={selectedOrg?.id || ""}
            onChange={(e) => handleOrgChange(e.target.value)}
            className="block w-full max-w-md rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>{org.name}</option>
            ))}
          </select>
        </div>
      )}

      {selectedOrg && (
        <>
          {/* Invite Form */}
          <div className="bg-white rounded-lg border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Invite Team Member</h2>
            <form onSubmit={handleInvite} className="flex gap-4 items-end">
              <div className="flex-1">
                <Input
                  label="Email"
                  type="email"
                  name="email"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm((p) => ({ ...p, email: e.target.value }))}
                  placeholder="colleague@company.com"
                />
              </div>
              <div className="w-48">
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm((p) => ({ ...p, role: e.target.value }))}
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  aria-label="Role"
                >
                  <option value="recruiter">Recruiter</option>
                  <option value="hr_manager">HR Manager</option>
                  <option value="organization_admin">Organization Admin</option>
                </select>
              </div>
              <Button type="submit" isLoading={isInviting} size="sm">Send Invitation</Button>
            </form>
            {inviteError && <p className="mt-2 text-sm text-red-600">{inviteError}</p>}
            {inviteSuccess && <p className="mt-2 text-sm text-green-600">{inviteSuccess}</p>}
          </div>

          {/* Members */}
          <div className="bg-white rounded-lg border">
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold text-gray-900">Team Members ({members.length})</h2>
            </div>
            <div className="divide-y">
              {members.map((m) => (
                <div key={m.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{m.user?.full_name || "Unknown"}</p>
                    <p className="text-sm text-gray-500">{m.user?.email}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${ROLE_COLORS[m.role] || "bg-gray-100 text-gray-800"}`}>
                      {ROLE_LABELS[m.role] || m.role}
                    </span>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[m.status] || "bg-gray-100 text-gray-800"}`}>
                      {m.status}
                    </span>
                    {m.user?.id !== user?.id && (
                      <button
                        onClick={() => handleToggleMemberStatus(m.id, m.status)}
                        className={`text-xs px-2 py-1 rounded ${
                          m.status === "active"
                            ? "text-yellow-600 hover:bg-yellow-50"
                            : "text-green-600 hover:bg-green-50"
                        }`}
                      >
                        {m.status === "active" ? "Suspend" : "Reactivate"}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {members.length === 0 && (
                <p className="p-4 text-sm text-gray-500">No team members found.</p>
              )}
            </div>
          </div>

          {/* Pending Invitations */}
          <div className="bg-white rounded-lg border">
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold text-gray-900">Pending Invitations ({invitations.filter((i) => i.status === "pending").length})</h2>
            </div>
            <div className="divide-y">
              {invitations.filter((i) => i.status === "pending").map((inv) => (
                <div key={inv.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{inv.email}</p>
                    <p className="text-sm text-gray-500">
                      {ROLE_LABELS[inv.role] || inv.role} • Expires {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : "N/A"}
                    </p>
                  </div>
                  <button
                    onClick={() => handleResendInvitation(inv.id)}
                    className="text-xs text-blue-600 hover:bg-blue-50 px-2 py-1 rounded"
                  >
                    Resend
                  </button>
                  <button
                    onClick={() => handleRevokeInvitation(inv.id)}
                    className="text-xs text-red-600 hover:bg-red-50 px-2 py-1 rounded"
                  >
                    Revoke
                  </button>
                </div>
              ))}
              {invitations.filter((i) => i.status === "pending").length === 0 && (
                <p className="p-4 text-sm text-gray-500">No pending invitations.</p>
              )}
            </div>
          </div>
        </>
      )}

      {organizations.length === 0 && (
        <div className="bg-white rounded-lg border p-6 max-w-lg mx-auto">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Create Your Organization</h2>
          <p className="text-sm text-gray-500 mb-4">You need an organization before you can manage team members.</p>
          <form onSubmit={handleCreateOrg} className="space-y-4">
            <Input
              label="Organization Name"
              type="text"
              value={orgForm.name}
              onChange={(e) => {
                const name = e.target.value;
                setOrgForm((p) => ({
                  ...p,
                  name,
                  slug: p.slug || name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
                }));
              }}
              placeholder="Acme Corp"
            />
            <Input
              label="Slug (URL-friendly identifier)"
              type="text"
              value={orgForm.slug}
              onChange={(e) => setOrgForm((p) => ({ ...p, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "") }))}
              placeholder="acme-corp"
            />
            {orgError && <p className="text-sm text-red-600">{orgError}</p>}
            <Button type="submit" isLoading={isCreatingOrg} size="sm">Create Organization</Button>
          </form>
        </div>
      )}
    </div>
  );
}
