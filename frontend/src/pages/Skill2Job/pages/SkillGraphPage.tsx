import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, Briefcase, GitBranch, RefreshCw } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { CuratedJob, JobSkillGraph, Skill2JobSkillGraph, SkillGraphNode } from "../../../types/skill2job";

const KIND_COLORS: Record<string, string> = {
  candidate: "#2563EB",
  gap: "#DC2626",
  related: "#9CA3AF",
  job: "#7C3AED",
  required: "#EA580C",
  preferred: "#0891B2",
  matched: "#16A34A",
};

const RELATION_LABELS: Record<string, string> = {
  synonym: "synonym",
  related: "related",
  transferable: "transferable",
  requires: "requires",
  prefers: "prefers",
};

const RELATION_COLORS: Record<string, string> = {
  synonym: "#7C3AED",
  related: "#94A3B8",
  transferable: "#059669",
  requires: "#EA580C",
  prefers: "#0891B2",
};

const LEGEND: Array<{ kind: string; label: string }> = [
  { kind: "candidate", label: "yours" },
  { kind: "gap", label: "gap" },
  { kind: "matched", label: "matched" },
  { kind: "related", label: "related" },
];

function layoutNodes(nodes: SkillGraphNode[], width: number, height: number) {
  const sized = nodes.slice(0, 120);
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) / 2 - 46;
  const result: Array<{ node: SkillGraphNode; x: number; y: number }> = [];
  sized.forEach((node, i) => {
    const angle = -Math.PI / 2 + (i / Math.max(sized.length, 1)) * Math.PI * 2;
    result.push({
      node,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    });
  });
  return result;
}

function GraphSVG({
  data,
  title,
  hint,
  legend,
}: {
  data: Skill2JobSkillGraph | JobSkillGraph;
  title: string;
  hint: string;
  legend: Array<{ kind: string; label: string }>;
}) {
  const width = 900;
  const height = 560;

  const nodes = data.nodes;
  const laid = useMemo(() => layoutNodes(nodes, width, height), [nodes]);
  const edges = data.edges.filter((e) => e.source < laid.length && e.target < laid.length);

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
        <div>
          <h3 className="text-sm font-bold text-gray-900">{title}</h3>
          <p className="text-xs text-gray-400">{hint}</p>
        </div>
        <div className="flex items-center gap-2">
          {legend.map((l) => (
            <span key={l.kind} className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500">
              <i className="h-2.5 w-2.5 rounded-full" style={{ background: KIND_COLORS[l.kind] }} /> {l.label}
            </span>
          ))}
        </div>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={title}
        className="h-auto w-full"
      >
        {edges.map((e, i) => {
          const s = laid[e.source];
          const t = laid[e.target];
          return (
            <g key={i}>
              <line
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke={RELATION_COLORS[e.relation] ?? RELATION_COLORS.related}
                strokeWidth={e.relation === "synonym" || e.relation === "requires" ? 2 : 1}
                strokeOpacity={e.relation === "related" ? 0.35 : 0.8}
              />
              <title>{`${s.node.label} — ${RELATION_LABELS[e.relation] ?? e.relation} — ${t.node.label}`}</title>
            </g>
          );
        })}
        {laid.map(({ node, x, y }, i) => {
          const isRelated = node.kind === "related";
          return (
            <g key={node.id}>
              <circle
                cx={x}
                cy={y}
                r={node.kind === "job" ? 22 : isRelated ? 9 : 16}
                fill={KIND_COLORS[node.kind] ?? KIND_COLORS.related}
                fillOpacity={node.kind === "candidate" ? 0.95 : node.kind === "gap" ? 0.9 : 0.6}
                stroke="#ffffff"
                strokeWidth={2}
              />
              <text
                x={x}
                y={y + 4}
                textAnchor="middle"
                fontSize={node.kind === "job" ? 11 : 9}
                fontWeight="700"
                fill="#ffffff"
                pointerEvents="none"
              >
                {node.kind === "related" ? "" : (node.label.slice(0, 2).toUpperCase() || `${i}`)}
              </text>
              <text x={x} y={y + (isRelated ? 24 : node.kind === "job" ? 38 : 30)} textAnchor="middle" fontSize={node.kind === "job" ? 11 : 10} fill="#374151">
                {node.kind === "job" ? node.label.slice(0, 26) : node.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="border-t border-gray-100 px-5 py-3">
        <p className="text-xs text-gray-400">
          {nodes.length} nodes · {edges.length} edges
        </p>
      </div>
    </div>
  );
}

export default function SkillGraphPage() {
  const [jobList, setJobList] = useState<CuratedJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [candidate, setCandidate] = useState<Skill2JobSkillGraph | null>(null);
  const [jobGraph, setJobGraph] = useState<JobSkillGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadCandidate() {
    setLoading(true);
    setError("");
    try {
      setCandidate(await skill2jobApi.getSkillGraph());
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      const msg = typeof d === "string" ? d : d?.msg ?? d?.message ?? "";
      setError(msg || "Could not load the skill graph.");
    } finally {
      setLoading(false);
    }
  }

  const onSelectJob = useCallback(async (jobId: string) => {
    setSelectedJobId(jobId);
    if (!jobId) {
      setJobGraph(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setJobGraph(await skill2jobApi.getJobSkillGraph(jobId));
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      const msg = typeof d === "string" ? d : d?.msg ?? d?.message ?? "";
      setError(msg || "Could not load this job's skill graph.");
      setJobGraph(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCandidate();
    skill2jobApi
      .getCatalog({ limit: 50 })
      .then((p) => setJobList(p.jobs))
      .catch(() => undefined);
  }, []);

  const data: Skill2JobSkillGraph | JobSkillGraph | null = selectedJobId && jobGraph ? jobGraph : candidate;
  const jobMatch = selectedJobId && jobGraph ? jobGraph.match : null;

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-gray-200 bg-white p-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <span className="ml-3 text-sm text-gray-500">Aggregating skill graph...</span>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-400" aria-hidden="true" />
        <p className="mt-3 text-sm text-red-700">{error || "Could not load the skill graph."}</p>
        <button
          onClick={() => {
            setSelectedJobId("");
            loadCandidate();
          }}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" /> Retry
        </button>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-12 text-center">
        <GitBranch className="mx-auto h-10 w-10 text-gray-300" aria-hidden="true" />
        <p className="mt-3 text-sm text-gray-500">
          No skills to visualize yet. Add skills via the My Profile page, then revisit here.
        </p>
      </div>
    );
  }

  const title = selectedJobId && jobGraph ? `${jobGraph.job.title}'s skill network` : "Your Skill Network";
  const hint =
    selectedJobId && jobGraph
      ? "Job skills (required/preferred/matched), your gaps and the SkillGraph relations tying them together."
      : "How your skills relate to each other and to the skills demanded by local jobs. Built from real profile + gap data.";

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
            <GitBranch className="h-5 w-5 text-primary-600" aria-hidden="true" />
            Skill Graph
          </h2>
          <div className="min-w-64">
            <label htmlFor="job-focus" className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              Focus on a job
            </label>
            <select
              id="job-focus"
              value={selectedJobId}
              onChange={(e) => onSelectJob(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 outline-none focus:border-primary-500"
            >
              <option value="">Your skills (whole catalog)</option>
              {jobList.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} — {j.company}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="mt-2 text-sm text-gray-500">{hint}</p>
        {jobMatch && (
          <div className="mt-3 flex flex-wrap gap-3 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-50 px-3 py-1 font-semibold text-primary-700 ring-1 ring-primary-200">
              <Briefcase className="h-3.5 w-3.5" aria-hidden="true" />
              match score {jobMatch.overall_score ?? "—"}
            </span>
            <span className="rounded-full bg-green-50 px-3 py-1 font-medium text-green-700 ring-1 ring-green-200">
              {jobMatch.matched_skills.length} matched
            </span>
            <span className="rounded-full bg-red-50 px-3 py-1 font-medium text-red-700 ring-1 ring-red-200">
              {jobMatch.missing_required.length} missing
            </span>
          </div>
        )}
      </section>

      <GraphSVG data={data} title={title} hint={hint} legend={LEGEND} />

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <h3 className="text-sm font-bold text-gray-900">Node detail</h3>
        <ul className="mt-3 divide-y divide-gray-100">
          {data.nodes.slice(0, 40).map((n) => (
            <li key={n.id} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-gray-800">
                  <span
                    className="mr-2 inline-block h-2.5 w-2.5 rounded-full"
                    style={{ background: KIND_COLORS[n.kind] }}
                  />
                  {n.label}
                </p>
                {n.category && <p className="text-xs text-gray-400">{n.category}</p>}
              </div>
              <span className="shrink-0 text-xs font-medium capitalize text-gray-500">{n.kind}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}