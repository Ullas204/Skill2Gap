import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { candidateApi } from "../../api/candidate";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type {
  ResumeIntelligenceReport,
  ResumeCompareReport,
} from "../../types/candidate";

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  return "bg-red-500";
}

export function ResumeIntelligence() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<ResumeIntelligenceReport | null>(null);
  const [compare, setCompare] = useState<ResumeCompareReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("scores");
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    if (!id) { setLoading(false); setError("No resume ID"); return; }
    async function load() {
      try {
        const [r, c] = await Promise.all([
          candidateApi.getResumeIntelligence(id!),
          candidateApi.compareResumeIntelligence(id!).catch(() => null),
        ]);
        if (!cancelledRef.current) {
          setReport(r);
          setCompare(c);
        }
      } catch { if (!cancelledRef.current) setError("Failed to load resume intelligence"); }
      finally { if (!cancelledRef.current) setLoading(false); }
    }
    load();
    return () => { cancelledRef.current = true; };
  }, [id]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (error || !report) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error || "No report available"}</div>;

  const { scores, strengths, weaknesses, ats_report, skill_analysis, keyword_analysis, recommendations, industry_keywords } = report;

  const tabs = [
    { key: "scores", label: "Scores" },
    { key: "ats", label: "ATS Report" },
    { key: "skills", label: "Skills" },
    { key: "keywords", label: "Keywords" },
    { key: "recommendations", label: "Recommendations" },
    { key: "compare", label: "Compare" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Resume Intelligence</h1>
          <p className="text-sm text-gray-500">{report.filename}</p>
        </div>
        <button onClick={() => navigate(`/candidate/resume/${id}`)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">&larr; Back to Resume</button>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)} className={`whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium ${tab === t.key ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>{t.label}</button>
          ))}
        </nav>
      </div>

      {tab === "scores" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(["overall", "completeness", "readability", "professionalism", "keyword_optimization", "ats_compatibility"] as const).map((key) => {
              const s = scores[key];
              return (
                <div key={key} className="rounded-lg border border-gray-200 bg-white p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-500">{s.label}</span>
                    <span className={`text-2xl font-bold ${scoreColor(s.score)}`}>{s.score}</span>
                  </div>
                  <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                    <div className={`h-full rounded-full ${scoreBg(s.score)} transition-all`} style={{ width: `${s.score}%` }} />
                  </div>
                  <p className="mt-2 text-xs text-gray-400">{s.description}</p>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="mb-3 text-sm font-semibold text-gray-900">Strengths</h3>
              {strengths.length === 0 ? <p className="text-sm text-gray-400">No strengths identified yet</p> : (
                <ul className="space-y-2">
                  {strengths.map((s, i) => <li key={i} className="flex items-start gap-2 text-sm text-gray-600"><span className="mt-0.5 text-green-500">&check;</span>{s}</li>)}
                </ul>
              )}
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="mb-3 text-sm font-semibold text-gray-900">Weaknesses</h3>
              {weaknesses.length === 0 ? <p className="text-sm text-gray-400">No weaknesses identified</p> : (
                <ul className="space-y-2">
                  {weaknesses.map((w, i) => <li key={i} className="flex items-start gap-2 text-sm text-gray-600"><span className="mt-0.5 text-red-500">&times;</span>{w}</li>)}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {tab === "ats" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center"><p className="text-2xl font-bold text-gray-900">{ats_report.section_count}/5</p><p className="text-xs text-gray-500">Sections</p></div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center"><p className="text-2xl font-bold text-gray-900">{ats_report.action_verb_count}</p><p className="text-xs text-gray-500">Action Verbs</p></div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center"><p className="text-2xl font-bold text-gray-900">{ats_report.quantifiable_achievements}</p><p className="text-xs text-gray-500">Quantified Items</p></div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center"><p className={`text-2xl font-bold ${ats_report.has_email && ats_report.has_phone ? "text-green-600" : "text-red-600"}`}>{ats_report.has_email && ats_report.has_phone ? "Yes" : "No"}</p><p className="text-xs text-gray-500">Contact Info</p></div>
          </div>

          {ats_report.formatting_issues.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4"><h4 className="mb-2 text-sm font-semibold text-red-800">Formatting Issues</h4><ul className="space-y-1">{ats_report.formatting_issues.map((issue, i) => <li key={i} className="text-sm text-red-700">&bull; {issue}</li>)}</ul></div>
          )}

          <div className="rounded-lg border border-gray-200 bg-white p-5">
            <h3 className="mb-3 text-sm font-semibold text-gray-900">Section Validation</h3>
            <div className="space-y-2">
              {Object.entries(ats_report.sections_valid).map(([section, valid]) => (
                <div key={section} className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2">
                  <span className="text-sm capitalize text-gray-700">{section.replace(/_/g, " ")}</span>
                  {valid ? <span className="text-xs font-medium text-green-600">Present</span> : <span className="text-xs font-medium text-red-500">Missing</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "skills" && (
        <div className="space-y-6">
          <div className="rounded-lg border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4"><h3 className="text-sm font-semibold text-gray-900">Skills ({skill_analysis.total_skills})</h3></div>
            <div className="flex flex-wrap gap-2">
              {skill_analysis.skill_names.map((s, i) => <span key={i} className="rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700">{s}</span>)}
              {skill_analysis.skill_names.length === 0 && <p className="text-sm text-gray-400">No skills extracted</p>}
            </div>
          </div>

          {Object.keys(skill_analysis.categorized).length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="mb-3 text-sm font-semibold text-gray-900">Categorized</h3>
              <div className="space-y-3">
                {Object.entries(skill_analysis.categorized).map(([cat, skills]) => (
                  <div key={cat}><p className="mb-1 text-xs font-medium uppercase text-gray-500">{cat.replace(/_/g, " ")}</p><div className="flex flex-wrap gap-1.5">{skills.map((s, i) => <span key={i} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">{s}</span>)}</div></div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {skill_analysis.missing_essential.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4"><h4 className="mb-2 text-sm font-semibold text-amber-800">Missing Essential Skills</h4><div className="flex flex-wrap gap-1.5">{skill_analysis.missing_essential.map((s, i) => <span key={i} className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700">{s}</span>)}</div></div>
            )}
            {skill_analysis.duplicates.length > 0 && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4"><h4 className="mb-2 text-sm font-semibold text-red-800">Duplicate Skills</h4><div className="flex flex-wrap gap-1.5">{skill_analysis.duplicates.map((s, i) => <span key={i} className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">{s}</span>)}</div></div>
            )}
          </div>

          {skill_analysis.suggestions.length > 0 && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4"><h4 className="mb-2 text-sm font-semibold text-blue-800">Trending Skills to Consider</h4><div className="flex flex-wrap gap-1.5">{skill_analysis.suggestions.map((s, i) => <span key={i} className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">{s}</span>)}</div></div>
          )}

          {Object.keys(industry_keywords).length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="mb-3 text-sm font-semibold text-gray-900">Industry Keywords</h3>
              <div className="space-y-3">
                {Object.entries(industry_keywords).map(([cat, data]) => (
                  <div key={cat} className="rounded-md bg-gray-50 p-3">
                    <p className="mb-1 text-xs font-medium uppercase text-gray-500">{cat.replace(/_/g, " ")}</p>
                    {data.matched.length > 0 && <div className="mb-2"><p className="text-xs text-gray-400">Matched:</p><div className="flex flex-wrap gap-1 mt-0.5">{data.matched.map((kw, i) => <span key={i} className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">{kw}</span>)}</div></div>}
                    {data.suggested.length > 0 && <div><p className="text-xs text-gray-400">Suggested:</p><div className="flex flex-wrap gap-1 mt-0.5">{data.suggested.map((kw, i) => <span key={i} className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">{kw}</span>)}</div></div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "keywords" && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center"><p className="text-2xl font-bold text-gray-900">{keyword_analysis.matched_action_keywords}/{keyword_analysis.total_action_keywords}</p><p className="text-xs text-gray-500">Keywords Matched</p></div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center"><p className="text-2xl font-bold text-gray-900">{Object.keys(keyword_analysis.keyword_density).length}</p><p className="text-xs text-gray-500">Unique Keywords</p></div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 text-center"><p className="text-2xl font-bold text-gray-900">{Object.values(keyword_analysis.keyword_density).reduce((a, b) => a + b, 0)}</p><p className="text-xs text-gray-500">Total Mentions</p></div>
          </div>

          {keyword_analysis.action_keywords_found.length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-5">
              <h3 className="mb-3 text-sm font-semibold text-gray-900">Found Keywords</h3>
              <div className="max-h-64 overflow-y-auto space-y-1">
                {Object.entries(keyword_analysis.keyword_density).sort(([, a], [, b]) => b - a).map(([kw, count]) => (
                  <div key={kw} className="flex items-center justify-between rounded px-2 py-1 text-sm hover:bg-gray-50"><span className="capitalize text-gray-700">{kw}</span><span className="text-xs text-gray-400">{count}x</span></div>
                ))}
              </div>
            </div>
          )}

          {keyword_analysis.action_keywords_missing.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4"><h4 className="mb-2 text-sm font-semibold text-amber-800">Missing Keywords</h4><div className="flex flex-wrap gap-1.5">{keyword_analysis.action_keywords_missing.map((kw, i) => <span key={i} className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700">{kw}</span>)}</div></div>
          )}
        </div>
      )}

      {tab === "recommendations" && (
        <div className="space-y-4">
          {recommendations.length === 0 ? <p className="text-sm text-gray-400">No recommendations</p> : (
            recommendations.map((r, i) => (
              <div key={i} className={`rounded-lg border p-4 ${r.priority === "high" ? "border-amber-200 bg-amber-50" : "border-gray-200 bg-white"}`}>
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${r.priority === "high" ? "bg-amber-200 text-amber-800" : "bg-gray-200 text-gray-600"}`}>{i + 1}</span>
                  <div><p className="text-sm text-gray-700">{r.text}</p></div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "compare" && (
        <div className="space-y-6">
          {compare ? (
            <>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="rounded-lg border border-gray-200 bg-white p-5">
                  <h3 className="mb-3 text-sm font-semibold text-gray-900">Current (v{compare.current.version})</h3>
                  <div className="space-y-2">{(["overall", "completeness", "readability", "professionalism", "keyword_optimization", "ats_compatibility"] as const).map((key) => {
                    const s = compare.current.scores[key];
                    const change = compare.score_changes[key];
                    return <div key={key} className="flex items-center justify-between text-sm"><span className="text-gray-500">{s.label}</span><span className="font-medium">{s.score}{change !== undefined && <span className={`ml-2 text-xs ${change >= 0 ? "text-green-600" : "text-red-600"}`}>{change >= 0 ? "+" : ""}{change}</span>}</span></div>;
                  })}</div>
                  <p className="mt-3 text-xs text-gray-400">{compare.current.total_skills} skills</p>
                </div>
                {compare.previous && (
                  <div className="rounded-lg border border-gray-200 bg-white p-5">
                    <h3 className="mb-3 text-sm font-semibold text-gray-900">Previous (v{compare.previous.version})</h3>
                    <div className="space-y-2">{(["overall", "completeness", "readability", "professionalism", "keyword_optimization", "ats_compatibility"] as const).map((key) => {
                      const s = compare.previous!.scores[key];
                      return <div key={key} className="flex items-center justify-between text-sm"><span className="text-gray-500">{s.label}</span><span className="font-medium">{s.score}</span></div>;
                    })}</div>
                    <p className="mt-3 text-xs text-gray-400">{compare.previous.total_skills} skills</p>
                  </div>
                )}
              </div>
              {compare.skills_added.length > 0 && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4"><h4 className="mb-2 text-sm font-semibold text-green-800">Skills Added</h4><div className="flex flex-wrap gap-1.5">{compare.skills_added.map((s, i) => <span key={i} className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">{s}</span>)}</div></div>
              )}
              {compare.skills_removed.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4"><h4 className="mb-2 text-sm font-semibold text-red-800">Skills Removed</h4><div className="flex flex-wrap gap-1.5">{compare.skills_removed.map((s, i) => <span key={i} className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">{s}</span>)}</div></div>
              )}
              {!compare.previous && <p className="text-sm text-gray-400">Only one version available. Upload another resume to compare.</p>}
            </>
          ) : <p className="text-sm text-gray-400">Comparison data not available.</p>}
        </div>
      )}
    </div>
  );
}
