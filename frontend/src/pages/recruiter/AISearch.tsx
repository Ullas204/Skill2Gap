import { useState } from "react";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { aiSearch } from "../../api/screening";
import type { AISearchResultItem, AISearchResponse } from "../../types/screening";

const SUGGESTION_QUERIES = [
  "Python developers with AWS",
  "React developers with 3 years experience",
  "Java Backend candidates",
  "Machine Learning Engineers",
  "Full stack developers with TypeScript",
  "DevOps engineers with Kubernetes",
  "Senior frontend developers remote",
  "Data scientists with Python and TensorFlow",
];

export function AISearchPage() {
  const { addToast } = useToast();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AISearchResponse | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch(q?: string) {
    const searchQuery = q || query;
    if (!searchQuery.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await aiSearch({ query: searchQuery, limit: 20 });
      setResults(data);
    } catch {
      addToast("Search failed. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleSearch();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Candidate Search</h1>
        <p className="mt-1 text-sm text-gray-500">Search candidates using natural language</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='e.g. "Python developers with AWS experience"'
            className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none"
          />
          <button
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
            className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {!searched && (
          <div className="mt-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Try these queries</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTION_QUERIES.map((sq) => (
                <button
                  key={sq}
                  onClick={() => { setQuery(sq); handleSearch(sq); }}
                  className="px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                >
                  {sq}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {loading && <LoadingSpinner size="lg" className="mt-10" />}

      {results && !loading && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              Found <span className="font-bold text-gray-900">{results.total}</span> candidates
              {results.query_skills.length > 0 && (
                <span className="ml-2">
                  matching <span className="font-medium text-primary-600">{results.query_skills.join(", ")}</span>
                </span>
              )}
            </p>
          </div>

          {results.results.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
              <p className="text-gray-500">No candidates found matching your query. Try broadening your search.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.results.map((r) => (
                <SearchResultCard key={r.candidate_id} result={r} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SearchResultCard({ result }: { result: AISearchResultItem }) {
  const relevanceColor =
    result.relevance_score >= 80 ? "text-green-600 bg-green-50" :
    result.relevance_score >= 60 ? "text-blue-600 bg-blue-50" :
    result.relevance_score >= 40 ? "text-yellow-600 bg-yellow-50" :
    "text-red-600 bg-red-50";

  const recLabel = result.recommendation.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const recColor =
    result.recommendation === "strongly_recommend" ? "text-green-700 bg-green-100" :
    result.recommendation === "recommend" ? "text-blue-700 bg-blue-100" :
    result.recommendation === "consider" ? "text-yellow-700 bg-yellow-100" :
    result.recommendation === "not_recommended" ? "text-red-700 bg-red-100" :
    "text-gray-600 bg-gray-100";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold text-gray-900">{result.candidate_name}</h3>
            <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${relevanceColor}`}>
              {result.relevance_score}% match
            </span>
            {result.overall_score > 0 && (
              <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                result.overall_score >= 80 ? "bg-green-100 text-green-800" :
                result.overall_score >= 60 ? "bg-blue-100 text-blue-800" :
                "bg-yellow-100 text-yellow-800"
              }`}>
                Score: {result.overall_score}%
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 mt-0.5">{result.candidate_email}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            {result.experience_years > 0 && <span>{result.experience_years} years exp</span>}
            {result.location && <span>{result.location}</span>}
          </div>
        </div>
        <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${recColor}`}>
          {recLabel}
        </span>
      </div>

      {result.matched_skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {result.matched_skills.slice(0, 8).map((s) => (
            <span key={s} className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full">{s}</span>
          ))}
        </div>
      )}
      {result.missing_skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {result.missing_skills.slice(0, 5).map((s) => (
            <span key={s} className="px-2 py-0.5 text-xs font-medium bg-red-50 text-red-600 rounded-full">{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}
