import { useCallback, useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import { useAuth } from "../../hooks/useAuth";
import type { CandidateProfile } from "../../types/candidate";

export function CandidateProfile() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchProfile = useCallback(async () => {
    try {
      const data = await candidateApi.getProfile();
      setProfile(data);
    } catch {
      setError("Failed to load profile");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    if (!profile) return;
    setProfile({ ...profile, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await candidateApi.updateProfile({
        phone: profile.phone,
        date_of_birth: profile.date_of_birth,
        gender: profile.gender,
        location: profile.location,
        nationality: profile.nationality,
        linkedin_url: profile.linkedin_url,
        github_url: profile.github_url,
        portfolio_url: profile.portfolio_url,
        website_url: profile.website_url,
        bio: profile.bio,
        current_role: profile.current_role,
      });
      setProfile(updated);
      setSuccess("Profile saved successfully");
    } catch {
      setError("Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const updated = await candidateApi.uploadAvatar(file);
      setProfile(updated);
      setSuccess("Avatar updated");
    } catch {
      setError("Failed to upload avatar");
    }
  };

  const handleRemoveAvatar = async () => {
    try {
      const updated = await candidateApi.removeAvatar();
      setProfile(updated);
    } catch {
      setError("Failed to remove avatar");
    }
  };

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your personal information
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}
      {success && (
        <div className="rounded-lg bg-green-50 p-3 text-sm text-green-600">{success}</div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Avatar</h2>
        <div className="flex items-center gap-4">
          {profile?.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt="Avatar"
              className="h-16 w-16 rounded-full object-cover"
            />
          ) : (
            <div className="h-16 w-16 rounded-full bg-gray-200 flex items-center justify-center text-gray-400">
              ?
            </div>
          )}
          <div className="flex gap-2">
            <label className="cursor-pointer">
              <span className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200">
                Upload
              </span>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={handleAvatarUpload}
              />
            </label>
            {profile?.avatar_url && (
              <Button variant="ghost" size="sm" onClick={handleRemoveAvatar}>
                Remove
              </Button>
            )}
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">
          Personal Information
        </h2>

        <div className="grid sm:grid-cols-2 gap-4">
          <Input
            label="Full Name"
            name="full_name"
            value={user?.full_name || ""}
            disabled
          />
          <Input
            label="Email"
            name="email"
            value={user?.email || ""}
            disabled
          />
        </div>

        <Input
          label="Current Role"
          name="current_role"
          value={profile?.current_role || ""}
          onChange={handleChange}
          placeholder="e.g. Senior Software Engineer"
        />

        <Input
          label="Phone"
          name="phone"
          value={profile?.phone || ""}
          onChange={handleChange}
          placeholder="+1 (555) 123-4567"
        />

        <div className="grid sm:grid-cols-2 gap-4">
          <Input
            label="Date of Birth"
            name="date_of_birth"
            type="date"
            value={profile?.date_of_birth || ""}
            onChange={handleChange}
          />
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-700">Gender</label>
            <select
              name="gender"
              value={profile?.gender || ""}
              onChange={handleChange}
              className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
            </select>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <Input
            label="Location"
            name="location"
            value={profile?.location || ""}
            onChange={handleChange}
            placeholder="City, Country"
          />
          <Input
            label="Nationality"
            name="nationality"
            value={profile?.nationality || ""}
            onChange={handleChange}
          />
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-700">Links</h3>
          <Input
            label="LinkedIn URL"
            name="linkedin_url"
            value={profile?.linkedin_url || ""}
            onChange={handleChange}
            placeholder="https://linkedin.com/in/..."
          />
          <Input
            label="GitHub URL"
            name="github_url"
            value={profile?.github_url || ""}
            onChange={handleChange}
            placeholder="https://github.com/..."
          />
          <Input
            label="Portfolio URL"
            name="portfolio_url"
            value={profile?.portfolio_url || ""}
            onChange={handleChange}
          />
          <Input
            label="Website"
            name="website_url"
            value={profile?.website_url || ""}
            onChange={handleChange}
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">Bio</label>
          <textarea
            name="bio"
            value={profile?.bio || ""}
            onChange={handleChange}
            rows={4}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Tell us about yourself..."
          />
        </div>

        <Button type="submit" isLoading={saving}>
          Save Profile
        </Button>
      </form>
    </div>
  );
}
