import { useCallback, useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { CandidateSkill, Skill } from "../../types/candidate";

const proficiencyOptions = ["beginner", "intermediate", "advanced", "expert"];

export function CandidateSkills() {
  const [skills, setSkills] = useState<CandidateSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Skill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [proficiency, setProficiency] = useState("intermediate");
  const [years, setYears] = useState("");

  const fetch = useCallback(async () => {
    try { setSkills(await candidateApi.listSkills()); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (q.length < 2) { setSearchResults([]); return; }
    try { setSearchResults(await candidateApi.searchSkills(q)); }
    catch { setSearchResults([]); }
  };

  const handleAdd = async () => {
    if (!selectedSkill) return;
    await candidateApi.addSkill({
      skill_id: selectedSkill.id,
      proficiency,
      years_of_experience: years ? parseFloat(years) : null,
    });
    setSelectedSkill(null);
    setSearchQuery("");
    setSearchResults([]);
    setProficiency("intermediate");
    setYears("");
    await fetch();
  };

  const handleRemove = async (skillId: number) => {
    await candidateApi.removeSkill(skillId);
    await fetch();
  };

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Skills</h1>
        <p className="mt-1 text-sm text-gray-500">Add and manage your skills</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-900">Add Skill</h2>
        <div className="relative">
          <Input
            label="Search Skills"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Type to search..."
          />
          {searchResults.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-40 overflow-y-auto">
              {searchResults.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 ${
                    selectedSkill?.id === s.id ? "bg-primary-50 text-primary-700" : ""
                  }`}
                  onClick={() => { setSelectedSkill(s); setSearchResults([]); setSearchQuery(s.name); }}
                >
                  {s.name}
                  <span className="text-xs text-gray-400 ml-2">({s.category})</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {selectedSkill && (
          <div className="flex items-center gap-3">
            <span className="text-sm bg-primary-50 text-primary-700 px-2 py-1 rounded">
              {selectedSkill.name}
            </span>
            <select
              value={proficiency}
              onChange={(e) => setProficiency(e.target.value)}
              className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
            >
              {proficiencyOptions.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <Input
              placeholder="Years"
              type="number"
              step="0.5"
              value={years}
              onChange={(e) => setYears(e.target.value)}
              className="w-20"
            />
            <Button size="sm" onClick={handleAdd}>Add</Button>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Your Skills ({skills.length})</h2>
        {skills.length === 0 ? (
          <p className="text-sm text-gray-400">No skills added yet.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {skills.map((cs) => (
              <div key={cs.skill_id} className="flex items-center gap-1 bg-gray-100 rounded-lg px-3 py-1.5 text-sm">
                <span className="font-medium">{cs.skill?.name || `Skill #${cs.skill_id}`}</span>
                <span className="text-xs text-gray-400">({cs.proficiency})</span>
                <button onClick={() => handleRemove(cs.skill_id)} className="ml-1 text-gray-400 hover:text-red-500">&times;</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
