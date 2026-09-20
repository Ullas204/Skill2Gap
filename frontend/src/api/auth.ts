import apiClient from "./client";
import type { LoginRequest, RegisterRequest, TokenResponse, User, Organization, Invitation, OrganizationMembership } from "../types/auth";

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/auth/login", data);
  return response.data;
}

export async function register(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>("/auth/register", data);
  return response.data;
}

export async function refreshToken(refreshToken: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return response.data;
}

export async function getMe(): Promise<User> {
  const response = await apiClient.get<User>("/auth/me");
  return response.data;
}

export async function logout(refreshToken?: string | null): Promise<void> {
  if (refreshToken) {
    await apiClient.post("/auth/logout", { refresh_token: refreshToken });
  } else {
    await apiClient.post("/auth/logout");
  }
}

// ── Organization APIs ──────────────────────────────────────────────

export async function getMyOrganizations(): Promise<Organization[]> {
  const response = await apiClient.get<Organization[]>("/organizations/me/list");
  return response.data;
}

export async function getOrganization(orgId: string): Promise<Organization> {
  const response = await apiClient.get<Organization>(`/organizations/${orgId}`);
  return response.data;
}

export async function createOrganization(data: { name: string; slug: string; description?: string; official_email?: string }): Promise<Organization> {
  const response = await apiClient.post<Organization>("/organizations", data);
  return response.data;
}

// ── Team Management APIs ──────────────────────────────────────────

export async function getOrgMembers(orgId: string): Promise<{ items: OrganizationMembership[]; total: number }> {
  const response = await apiClient.get(`/organizations/${orgId}/members`);
  return response.data;
}

export async function inviteMember(orgId: string, email: string, role: string): Promise<Invitation> {
  const response = await apiClient.post(`/organizations/${orgId}/invitations`, { email, role });
  return response.data;
}

export async function getOrgInvitations(orgId: string): Promise<{ items: Invitation[]; total: number }> {
  const response = await apiClient.get(`/organizations/${orgId}/invitations`);
  return response.data;
}

export async function revokeInvitation(orgId: string, invitationId: string): Promise<void> {
  await apiClient.post(`/organizations/${orgId}/invitations/${invitationId}/revoke`);
}

export async function resendInvitation(orgId: string, invitationId: string): Promise<Invitation> {
  const response = await apiClient.post(`/organizations/${orgId}/invitations/${invitationId}/resend`);
  return response.data;
}

export async function updateMemberStatus(orgId: string, membershipId: string, status: string): Promise<void> {
  await apiClient.put(`/organizations/${orgId}/members/${membershipId}/status`, { status });
}

export async function validateInvitation(token: string): Promise<{ valid: boolean; email?: string; role?: string; organization_name?: string; expires_at?: string; status?: string; existing_user?: boolean }> {
  const response = await apiClient.get(`/invitations/validate/${token}`);
  return response.data;
}

export async function acceptInvitation(data: { token: string; full_name: string; password: string; confirm_password: string }): Promise<void> {
  await apiClient.post("/invitations/accept", data);
}

export async function acceptSignedInInvitation(token: string): Promise<void> {
  await apiClient.post("/invitations/accept-signed-in", { token });
}
