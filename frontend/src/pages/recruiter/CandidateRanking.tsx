import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { MatchScoreCard } from "../../components/screening/MatchScoreCard";
import { useToast } from "../../contexts/ToastContext";
import { screenJobApplicants, getJobRankings, getScreeningResult } from "../../api/screening";
import type { CandidateRanking, ScreeningResult } from "../../types/screening";

export function RecruiterCandidateRanking() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [rankings, setRankings] = useState<CandidateRanking[]>([]);
  const [selectedRanking, setSelectedRanking] = useState<CandidateRanking | null>(null);
  const [selectedScreening, setSelectedScreening] = useState<ScreeningResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [screeningLoading, setScreeningLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!id) return;
    async function load() {
      try {
        const data = await getJobRankings(id!);
        setRankings(data.items);
      } catch {
        addToast("Failed to load rankings", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, addToast]);

  async function handleScreenAll() {
    if (!id) return;
    setScanning(true);
    try {
      const result = await screenJobApplicants(id);
      addToast(`Screened ${result.candidates_screened} candidates`, "success");
      const data = await getJobRankings(id);
      setRankings(data.items);
    } catch {
      addToast("Failed to screen candidates", "error");
    } finally {
      setScanning(false);
    }
  }

  async function handleViewDetails(candidateId: string) {
    if (!id) return;
    setScreeningLoading(true);
    try {
      const data = await getScreeningResult(id, candidateId);
      setSelectedScreening(data);
      const ranking = rankings.find((r) => r.candidate_id === candidateId);
      if (ranking) setSelectedRanking(ranking);
    } catch {
      addToast("Failed to load screening details", "error");
    } finally {
      setScreeningLoading(false);
    }
  }

  function toggleCompare(candidateId: string) {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(candidateId)) next.delete(candidateId);
      else if (next.size < 4) next.add(candidateId);
      return next;
    });
  }

  function handleCompare() {
    if (compareIds.size >= 2 && id) {
      navigate(`/recruiter/jobs/${id}/compare?ids=${Array.from(compareIds).join(",")}`);
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Candidate Rankings</h1>
          <p className="mt-1 text-sm text-gray-500">{rankings.length} candidates ranked by AI matching</p>
        </div>
        <div className="flex gap-2">
          {compareIds.size >= 2 && (
            <button
              onClick={handleCompare}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Compare ({compareIds.size})
            </button>
          )}
          <button
            onClick={handleScreenAll}
            disabled={scanning}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {scanning ? "Screening..." : "Screen All Candidates"}
          </button>
        </div>
      </div>

      {rankings.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No candidates have been screened yet.</p>
          <button
            onClick={handleScreenAll}
            disabled={scanning}
            className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Screen all candidates now
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <div className="rounded-lg border bg-white">
              <div className="border-b px-4 py-3">
                <h2 className="font-semibold text-gray-900">Ranked Candidates</h2>
              </div>
              <div className="divide-y max-h-[600px] overflow-y-auto">
                {rankings.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => handleViewDetails(r.candidate_id)}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-50 ${selectedRanking?.id === r.id ? "bg-primary-50" : ""}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={compareIds.has(r.candidate_id)}
                          onChange={(e) => { e.stopPropagation(); toggleCompare(r.candidate_id); }}
                          onClick={(e) => e.stopPropagation()}
                          className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-gray-400">#{r.rank}</span>
                            <p className="text-sm font-medium text-gray-900">{r.candidate_name}</p>
                          </div>
                          <p className="text-xs text-gray-500">{r.candidate_email}</p>
                        </div>
                      </div>
                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                        r.overall_score >= 80 ? "bg-green-100 text-green-800" :
                        r.overall_score >= 60 ? "bg-blue-100 text-blue-800" :
                        r.overall_score >= 40 ? "bg-yellow-100 text-yellow-800" :
                        "bg-red-100 text-red-800"
                      }`}>
                        {r.overall_score}%
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            {screeningLoading ? (
              <LoadingSpinner size="md" className="mt-10" />
            ) : selectedScreening ? (
              <MatchScoreCard
                screening={selectedScreening}
                candidateName={selectedRanking?.candidate_name}
              />
            ) : (
              <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
                <p className="text-gray-500">Select a candidate to view their screening details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
