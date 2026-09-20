import { useEffect, useState } from "react";
import { FileText, Mic, Sparkles, Upload } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { PerceptionDetail, PerceptionRecord } from "../../../types/skill2job";
import { extractErrorMessage } from "./shared";
import { PerceptionDetailPanel } from "../PerceptionDetailPanel";

/** Perceive a resume/document/text/voice and review the provenance-annotated extraction history. */
export function PerceptionSection() {
  const [history, setHistory] = useState<PerceptionRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"success" | "partial" | "error">("success");
  const [failed, setFailed] = useState(false);
  const [processingSteps, setProcessingSteps] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<PerceptionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function refresh() {
    try {
      const res = await skill2jobApi.getPerceptions();
      setHistory(res.items);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function loadDetail(id: string) {
    if (selectedId === id) {
      setSelectedId(null);
      setDetail(null);
      return;
    }
    setSelectedId(id);
    setDetailLoading(true);
    setDetail(null);
    try {
      const d = await skill2jobApi.getPerceptionDetail(id);
      setDetail(d);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }

  async function deletePerception(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Delete this perception record?")) return;
    setDeletingId(id);
    try {
      await skill2jobApi.deletePerception(id);
      if (selectedId === id) {
        setSelectedId(null);
        setDetail(null);
      }
      await refresh();
    } catch {
      // silently fail
    } finally {
      setDeletingId(null);
    }
  }

  async function onFile(file: File | null) {
    if (!file) return;
    setBusy(true);
    setMessage("");
    setProcessingSteps([]);

    const steps = ["Validating file...", "Extracting text...", "Analyzing layout...", "Detecting sections...", "Identifying skills..."];
    for (let i = 0; i < steps.length; i++) {
      await new Promise((r) => setTimeout(r, 300));
      setProcessingSteps(steps.slice(0, i + 1));
    }

    try {
      const res = await skill2jobApi.uploadResume(file);
      const status = res.processing_status as string;
      const skillCount = (res.skill_count as number) ?? 0;
      const processingMsg = res.processing_message as string | null;

      if (status === "failed") {
        setMessageType("error");
        setMessage(String(processingMsg || `Could not parse "${file.name}". Try a PDF, text file, or pasted text.`));
      } else if (status === "partial") {
        setMessageType("partial");
        setMessage(
          `Partial parse of "${file.name}" — ${skillCount} skills extracted.` +
            (processingMsg ? ` ${processingMsg}` : " Some fields may be missing.")
        );
      } else {
        setMessageType("success");
        setMessage(`Successfully parsed "${file.name}" — ${skillCount} skills extracted.`);
      }
      await refresh();
      if (res.perception_id) {
        await loadDetail(res.perception_id);
      }
    } catch (err: any) {
      setMessageType("error");
      const detail = err?.response?.data?.detail;
      const msg = extractErrorMessage(detail);
      setMessage(msg || "Could not parse that document. Try a PDF, text file, or pasted text.");
    } finally {
      setBusy(false);
      setProcessingSteps([]);
    }
  }

  const [text, setText] = useState("");
  async function submitText() {
    if (!text.trim()) return;
    setBusy(true);
    setMessage("");
    setProcessingSteps([]);

    const steps = ["Analyzing text...", "Extracting skills...", "Normalizing..."];
    for (let i = 0; i < steps.length; i++) {
      await new Promise((r) => setTimeout(r, 200));
      setProcessingSteps(steps.slice(0, i + 1));
    }

    try {
      const res = await skill2jobApi.perceiveText(text);
      const status = res.processing_status as string;
      const skillCount = (res.skill_count as number) ?? 0;

      if (status === "failed") {
        setMessageType("error");
        setMessage("Could not extract skills from the provided text.");
      } else if (status === "partial") {
        setMessageType("partial");
        setMessage(`Partial result — ${skillCount} skills detected from free text.`);
      } else {
        setMessageType("success");
        setMessage(`Extracted ${skillCount} skills from free text.`);
      }
      setText("");
      await refresh();
      if (res.perception_id) {
        await loadDetail(res.perception_id);
      }
    } catch (err: any) {
      setMessageType("error");
      const detail = err?.response?.data?.detail;
      const msg = extractErrorMessage(detail);
      setMessage(msg || "Could not parse that text.");
    } finally {
      setBusy(false);
      setProcessingSteps([]);
    }
  }

  return (
    <div className="space-y-6">
      {selectedId &&
        (detailLoading ? (
          <div className="flex items-center justify-center rounded-2xl border border-gray-200 bg-white p-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
            <span className="ml-3 text-sm text-gray-500">Loading parsed details...</span>
          </div>
        ) : detail ? (
          <PerceptionDetailPanel detail={detail} onBack={() => { setSelectedId(null); setDetail(null); }} />
        ) : (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            Failed to load perception details.
          </div>
        ))}

      {!selectedId && (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-gray-200 bg-white p-6">
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <Upload className="h-5 w-5 text-primary-600" aria-hidden="true" />
              Perceive a Resume or Document
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              PDF, text, image, or audio. Skills are extracted with provenance and written to your
              normalized skill profile.
            </p>
            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 px-6 py-10 text-center transition-colors hover:border-primary-300 hover:bg-primary-50">
              <FileText className="h-8 w-8 text-gray-400" aria-hidden="true" />
              <span className="mt-2 text-sm font-semibold text-gray-700">Choose a file to upload</span>
              <span className="mt-1 text-xs text-gray-400">resume.pdf · resume.txt · notes.png · voice.wav</span>
              <input
                type="file"
                accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.wav,.mp3,.ogg"
                className="sr-only"
                onChange={(e) => onFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-6">
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <Mic className="h-5 w-5 text-primary-600" aria-hidden="true" />
              Perceive Free Text or Voice
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Paste your experience summary. On-device transcription adapts to available providers.
            </p>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={5}
              className="mt-4 w-full rounded-xl border border-gray-300 p-3 text-sm text-gray-800 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
              placeholder="e.g. I have 3+ years building data pipelines with Python and Apache Airflow..."
            />
            <button
              type="button"
              disabled={busy}
              onClick={submitText}
              className="mt-3 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Extract skills
            </button>
          </section>
        </div>
      )}

      {processingSteps.length > 0 && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            <span className="text-sm font-medium text-blue-800">Processing document...</span>
          </div>
          <ul className="mt-2 space-y-1">
            {processingSteps.map((step, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-blue-600">
                <span className="text-green-500">&#10003;</span> {step}
              </li>
            ))}
          </ul>
        </div>
      )}

      {message && (
        <div className={`rounded-xl border p-4 text-sm ${
          messageType === "success"
            ? "border-green-200 bg-green-50 text-green-800"
            : messageType === "partial"
            ? "border-amber-200 bg-amber-50 text-amber-800"
            : "border-red-200 bg-red-50 text-red-800"
        }`}>
          {messageType === "success" && <span className="mr-1">&#10003;</span>}
          {messageType === "partial" && <span className="mr-1">&#9888;</span>}
          {messageType === "error" && <span className="mr-1">&#10007;</span>}
          {message}
        </div>
      )}

      {!selectedId && (
        <section className="rounded-2xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-bold text-gray-900">Perception History</h2>
          {failed ? (
            <p className="mt-2 text-sm text-gray-400">No perceptions yet.</p>
          ) : history.length === 0 ? (
            <p className="mt-2 text-sm text-gray-400">No perceptions yet. Upload a resume or paste text above.</p>
          ) : (
            <ul className="mt-4 divide-y divide-gray-100">
              {history.map((r) => (
                <li
                  key={r.id}
                  onClick={() => loadDetail(r.id)}
                  className="flex cursor-pointer items-start justify-between gap-4 rounded-xl p-3 transition-colors hover:bg-gray-50"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-gray-800">
                      {r.original_filename || "Free Text Input"}{" "}
                      <span className="text-xs font-normal text-gray-400">&middot; {r.input_type}</span>
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        r.processing_status === "ok"
                          ? "bg-green-50 text-green-700"
                          : r.processing_status === "partial"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-red-50 text-red-600"
                      }`}>
                        {r.processing_status}
                      </span>
                      {r.field_confidence != null && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                          {Math.round(r.field_confidence * 100)}%
                        </span>
                      )}
                      {r.skills_count > 0 && (
                        <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                          {r.skills_count} skills
                        </span>
                      )}
                      {r.experience_count > 0 && (
                        <span className="inline-flex items-center rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                          {r.experience_count} exp
                        </span>
                      )}
                      {r.education_count > 0 && (
                        <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                          {r.education_count} edu
                        </span>
                      )}
                    </div>
                    {r.processing_message && (
                      <p className="mt-1 text-xs text-gray-500">{r.processing_message}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-gray-400">{new Date(r.created_at).toLocaleDateString()}</span>
                    <button
                      onClick={(e) => deletePerception(r.id, e)}
                      disabled={deletingId === r.id}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-red-500 transition-colors hover:bg-red-50 hover:text-red-700 disabled:opacity-50"
                      title="Delete this perception"
                    >
                      {deletingId === r.id ? "..." : "Delete"}
                    </button>
                    <span className="text-xs font-medium text-primary-600">View Details &rarr;</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}