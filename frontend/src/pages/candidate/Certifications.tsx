import { useCallback, useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { Certification, CertificationFormData } from "../../types/candidate";

export function CandidateCertifications() {
  const [records, setRecords] = useState<Certification[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState<CertificationFormData>({ name: "", organization: "" });

  const fetch = useCallback(async () => {
    try { setRecords(await candidateApi.listCertifications()); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const resetForm = () => setForm({ name: "", organization: "" });

  const handleEdit = (r: Certification) => {
    setEditing(r.id);
    setForm({ name: r.name, organization: r.organization, issue_date: r.issue_date, expiry_date: r.expiry_date, credential_id: r.credential_id || "", credential_url: r.credential_url || "" });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) { await candidateApi.updateCertification(editing, form); }
      else { await candidateApi.createCertification(form); }
      resetForm(); setEditing(null); await fetch();
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    await candidateApi.deleteCertification(id);
    await fetch();
  };

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Certifications</h1>
        <p className="mt-1 text-sm text-gray-500">Add your professional certifications</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-900">{editing ? "Edit Certification" : "Add Certification"}</h2>
        <Input label="Certification Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <Input label="Organization" value={form.organization} onChange={(e) => setForm({ ...form, organization: e.target.value })} required />
        <div className="grid grid-cols-2 gap-4">
          <Input label="Issue Date" type="date" value={form.issue_date || ""} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} />
          <Input label="Expiry Date" type="date" value={form.expiry_date || ""} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} />
        </div>
        <Input label="Credential ID" value={form.credential_id || ""} onChange={(e) => setForm({ ...form, credential_id: e.target.value })} />
        <Input label="Credential URL" value={form.credential_url || ""} onChange={(e) => setForm({ ...form, credential_url: e.target.value })} />
        <div className="flex gap-2">
          <Button type="submit">{editing ? "Update" : "Add"}</Button>
          {editing && <Button variant="ghost" onClick={() => { resetForm(); setEditing(null); }}>Cancel</Button>}
        </div>
      </form>

      <div className="space-y-3">
        {records.length === 0 && <p className="text-sm text-gray-400">No certifications added yet.</p>}
        {records.map((r) => (
          <div key={r.id} className="bg-white rounded-xl border border-gray-200 p-4 flex justify-between items-start">
            <div>
              <p className="font-medium text-gray-900">{r.name}</p>
              <p className="text-sm text-gray-500">{r.organization}</p>
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
