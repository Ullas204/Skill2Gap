import type { CandidateProfile } from "../../types/candidate";

interface WelcomeCardProps {
  fullName: string;
  profile: CandidateProfile;
}

export function WelcomeCard({ fullName, profile }: WelcomeCardProps) {
  const initials = fullName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="bg-gradient-to-br from-primary-600 to-primary-800 rounded-xl p-6 text-white">
      <div className="flex items-center gap-4">
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={fullName}
            className="h-16 w-16 rounded-full object-cover border-2 border-white/30"
          />
        ) : (
          <div className="h-16 w-16 rounded-full bg-white/20 flex items-center justify-center text-xl font-bold">
            {initials}
          </div>
        )}
        <div>
          <h2 className="text-xl font-bold">{fullName}</h2>
          <p className="text-white/80 text-sm">
            {profile.current_role || "Candidate"}
          </p>
        </div>
      </div>
      <div className="mt-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-white/20 rounded-full h-2">
            <div
              className="bg-white rounded-full h-2 transition-all"
              style={{ width: `${profile.profile_completion}%` }}
            />
          </div>
          <span className="text-sm font-medium">{profile.profile_completion}%</span>
        </div>
        <p className="text-white/70 text-xs mt-1">Profile completion</p>
      </div>
    </div>
  );
}
