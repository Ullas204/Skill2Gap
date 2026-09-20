import { useCallback, useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { Project, ProjectFormData } from "../../types/candidate";

export function CandidateProjects() {
  const [records, setRecords] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState<ProjectFormData>({ title: "" });

  const fetch = useCallback(async () => {
    try { setRecords(await candidateApi.listProjects()); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const resetForm = () => setForm({ title: "" });
  const handleEdit = (r: Project) => {
    setEditing(r.id);
    setForm({
      title: r.title, description: r.description || "",
      technologies: r.technologies || "", github_link: r.github_link || "",
      live_demo: r.live_demo || "", start_date: r.start_date, end_date: r.end_date,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) { await candidateApi.updateProject(editing, form); }
      else { await candidateApi.createProject(form); }
      resetForm(); setEditing(null); await fetch();
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    await candidateApi.deleteProject(id);
    await fetch();
  };

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <p className="mt-1 text-sm text-gray-500">Showcase your work</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-900">{editing ? "Edit Project" : "Add Project"}</h2>
        <Input label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-700">Description</label>
          <textarea value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3}
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" />
        </div>
        <Input label="Technologies" value={form.technologies || ""} onChange={(e) => setForm({ ...form, technologies: e.target.value })} placeholder="React, Node.js, PostgreSQL" />
        <Input label="GitHub Link" value={form.github_link || ""} onChange={(e) => setForm({ ...form, github_link: e.target.value })} />
        <Input label="Live Demo" value={form.live_demo || ""} onChange={(e) => setForm({ ...form, live_demo: e.target.value })} />
        <div className="grid grid-cols-2 gap-4">
          <Input label="Start Date" type="date" value={form.start_date || ""} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          <Input label="End Date" type="date" value={form.end_date || ""} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
        </div>
        <div className="flex gap-2">
          <Button type="submit">{editing ? "Update" : "Add"}</Button>
          {editing && <Button variant="ghost" onClick={() => { resetForm(); setEditing(null); }}>Cancel</Button>}
        </div>
      </form>

      <div className="space-y-3">
        {records.length === 0 && <p className="text-sm text-gray-400">No projects added yet.</p>}
        {records.map((r) => (
          <div key={r.id} className="bg-white rounded-xl border border-gray-200 p-4 flex justify-between items-start">
            <div>
              <p className="font-medium text-gray-900">{r.title}</p>
              {r.technologies && <p className="text-xs text-gray-400 mt-1">{r.technologies}</p>}
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
