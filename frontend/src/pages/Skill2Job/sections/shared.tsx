import { Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/** Safely extract a displayable string from any API error detail. */
export function extractErrorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "object" && first !== null) {
      return (first as any).msg || (first as any).message || (first as any).detail || JSON.stringify(first);
    }
    return String(first);
  }
  if (typeof detail === "object" && detail !== null) {
    return (detail as any).msg || (detail as any).message || (detail as any).detail || JSON.stringify(detail);
  }
  return "";
}

export function SnapshotStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</p>
      <p className="text-2xl font-extrabold text-primary-700">{value}</p>
    </div>
  );
}

export function SkillsSectionHeader({
  icon: Icon,
  title,
  hint,
  cta,
  onClick,
  busy,
}: {
  icon: LucideIcon;
  title: string;
  hint: string;
  cta: string;
  onClick: () => void;
  busy: boolean;
}) {
  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="max-w-2xl">
          <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
            <Icon className="h-5 w-5 text-primary-600" aria-hidden="true" />
            {title}
          </h2>
          <p className="mt-1 text-sm text-gray-500">{hint}</p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={onClick}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
        >
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          {busy ? "Working…" : cta}
        </button>
      </div>
    </section>
  );
}

export function StatusCard({ label, ok, caption }: { label: string; ok: boolean; caption: string }) {
  return (
    <div
      className={`rounded-2xl border p-5 ${
        ok ? "border-green-200 bg-green-50/60" : "border-gray-200 bg-white"
      }`}
    >
      <p className="text-sm font-semibold text-gray-900">{label}</p>
      <p className="mt-0.5 text-xs text-gray-500">{caption}</p>
      <p className="mt-2 text-xs font-bold uppercase tracking-wide text-gray-500">
        <span className={ok ? "text-green-600" : "text-gray-400"}>{ok ? "Ready" : "Pending"}</span>
      </p>
    </div>
  );
}