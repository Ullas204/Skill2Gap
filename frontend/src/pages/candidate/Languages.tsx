import { useCallback, useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { Language, LanguageFormData } from "../../types/candidate";

const levels = ["beginner", "elementary", "intermediate", "advanced", "native"];

export function CandidateLanguages() {
  const [records, setRecords] = useState<Language[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState<LanguageFormData>({ language: "", reading: "intermediate", writing: "intermediate", speaking: "intermediate" });

  const fetch = useCallback(async () => {
    try { setRecords(await candidateApi.listLanguages()); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const resetForm = () => setForm({ language: "", reading: "intermediate", writing: "intermediate", speaking: "intermediate" });

  const handleEdit = (r: Language) => {
    setEditing(r.id);
    setForm({ language: r.language, reading: r.reading, writing: r.writing, speaking: r.speaking });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) { await candidateApi.updateLanguage(editing, form); }
      else { await candidateApi.createLanguage(form); }
      resetForm(); setEditing(null); await fetch();
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    await candidateApi.deleteLanguage(id);
    await fetch();
  };

  const LevelSelect = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="block w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500">
      {levels.map((l) => <option key={l} value={l}>{l}</option>)}
    </select>
  );

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Languages</h1>
        <p className="mt-1 text-sm text-gray-500">Add languages you speak</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-900">{editing ? "Edit Language" : "Add Language"}</h2>
        <Input label="Language" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} required placeholder="e.g. English, Spanish" />
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1">
            <label className="block text-xs font-medium text-gray-600">Reading</label>
            <LevelSelect value={form.reading || "intermediate"} onChange={(v) => setForm({ ...form, reading: v })} />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-gray-600">Writing</label>
            <LevelSelect value={form.writing || "intermediate"} onChange={(v) => setForm({ ...form, writing: v })} />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-gray-600">Speaking</label>
            <LevelSelect value={form.speaking || "intermediate"} onChange={(v) => setForm({ ...form, speaking: v })} />
          </div>
        </div>
        <div className="flex gap-2">
          <Button type="submit">{editing ? "Update" : "Add"}</Button>
          {editing && <Button variant="ghost" onClick={() => { resetForm(); setEditing(null); }}>Cancel</Button>}
        </div>
      </form>

      <div className="space-y-3">
        {records.length === 0 && <p className="text-sm text-gray-400">No languages added yet.</p>}
        {records.map((r) => (
          <div key={r.id} className="bg-white rounded-xl border border-gray-200 p-4 flex justify-between items-start">
            <div>
              <p className="font-medium text-gray-900">{r.language}</p>
              <p className="text-xs text-gray-400">R:{r.reading} W:{r.writing} S:{r.speaking}</p>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => handleEdit(r)}>Edit</Button>
              <Button variant="ghost" size="sm" onClick={() => handleDelete(r.id)}>Delete</Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
