import { useEffect, useState } from "react";
import { AlertCircle, BadgeCheck, FileSearch, RefreshCw, ShieldCheck } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { Skill2JobSkillProof, SkillProofItem } from "../../../types/skill2job";

const SOURCE_LABELS: Record<string, string> = {
  profile: "Candidate profile",
  perception: "Document perception",
  matched_jobs: "Matched jobs",
  gap_demand: "Job demand (gaps)",
};

const SOURCE_BADGES: Record<string, string> = {
  profile: "bg-blue-50 text-blue-700",
  perception: "bg-purple-50 text-purple-700",
  matched_jobs: "bg-green-50 text-green-700",
  gap_demand: "bg-amber-50 text-amber-700",
};

function EvidenceList({ item }: { item: SkillProofItem }) {
  if (item.evidence.length === 0) {
    return <p className="mt-2 text-xs text-gray-400">Listed on your profile but no additional evidence yet.</p>;
  }
  return (
    <ul className="mt-2 space-y-1.5">
      {item.evidence.map((e, i) => (
        <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
          <span
            className={`mt-0.5 inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
              SOURCE_BADGES[e.source] ?? "bg-gray-100 text-gray-600"
            }`}
          >
            {SOURCE_LABELS[e.source] ?? e.source}
          </span>
          <span>{e.note}</span>
        </li>
      ))}
    </ul>
  );
}

export default function SkillProofPage() {
  const [data, setData] = useState<Skill2JobSkillProof | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await skill2jobApi.getSkillProof());
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      const msg = typeof d === "string" ? d : d?.msg ?? d?.message ?? "";
      setError(msg || "Could not load skill evidence.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = (data?.skills ?? []).filter((s) =>
    query.trim() ? s.name.toLowerCase().includes(query.trim().toLowerCase()) : true
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-gray-200 bg-white p-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <span className="ml-3 text-sm text-gray-500">Aggregating skill evidence...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-400" aria-hidden="true" />
        <p className="mt-3 text-sm text-red-700">{error || "Could not load skill evidence."}</p>
        <button
          onClick={load}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" /> Retry
        </button>
      </div>
    );
  }

  if (data.skills.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-12 text-center">
        <FileSearch className="mx-auto h-10 w-10 text-gray-300" aria-hidden="true" />
        <p className="mt-3 text-sm text-gray-500">
          No skills to prove yet. Add skills via the My Profile page or upload a resume.
        </p>
      </div>
    );
  }

  const sourceChip = (label: string, count: number): string => `${label}: ${count}`;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
          <ShieldCheck className="h-5 w-5 text-primary-600" aria-hidden="true" />
          Skill Proof Medium
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Every skill below is backed by real evidence aggregated from your profile, perceived
          documents, matched jobs, and job-demand gaps. Nothing is invented.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(data.sources)
            .filter(([, n]) => n > 0)
            .map(([key, n]) => (
              <span key={key} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${SOURCE_BADGES[key] ?? "bg-gray-100 text-gray-600"}`}>
                {sourceChip(SOURCE_LABELS[key] ?? key, n)}
              </span>
            ))}
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter skills…"
          className="mt-4 w-full max-w-sm rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
        />
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        {filtered.length === 0 && (
          <p className="text-sm text-gray-400">No skills match “{query}”.</p>
        )}
        {filtered.map((item) => (
          <section key={item.name} className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-gray-900">{item.name}</p>
                <p className="text-xs text-gray-500">
                  {item.category ?? "Uncategorized"}
                  {item.proficiency ? ` · ${item.proficiency}` : ""}
                  {item.years != null ? ` · ${item.years} yrs` : ""}
                </p>
              </div>
              <BadgeCheck className="h-5 w-5 shrink-0 text-green-500" aria-hidden="true" />
            </div>
            <EvidenceList item={item} />
          </section>
        ))}
      </div>
    </div>
  );
}