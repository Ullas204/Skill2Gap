import type { Resume } from "../../types/candidate";

interface ResumeCardProps {
  resume: Resume;
  onView?: (id: string) => void;
  onDelete?: (id: string) => void;
  onSetPrimary?: (id: string) => void;
}

const FILE_ICONS: Record<string, string> = {
  pdf: "\u{1F4C4}",
  docx: "\u{1F4DD}",
  doc: "\u{1F4DD}",
  txt: "\u{1F4C4}",
  html: "\u{1F310}",
  htm: "\u{1F310}",
  rtf: "\u{1F4C4}",
};

const STATUS_COLORS: Record<string, string> = {
  uploaded: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  parsed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ResumeCard({ resume, onView, onDelete, onSetPrimary }: ResumeCardProps) {
  const icon = FILE_ICONS[resume.file_type] || "\u{1F4C4}";
  const statusColor = STATUS_COLORS[resume.status] || "bg-gray-100 text-gray-800";

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-sm">
      <div className="flex items-center gap-4">
        <span className="text-2xl">{icon}</span>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-gray-900">
            {resume.original_filename}
            {resume.is_primary && (
              <span className="ml-2 inline-flex items-center rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700">
                Primary
              </span>
            )}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span>{formatFileSize(resume.file_size)}</span>
            <span className="text-gray-300">|</span>
            <span>{resume.file_type.toUpperCase()}</span>
            {resume.language && (
              <>
                <span className="text-gray-300">|</span>
                <span>{resume.language.toUpperCase()}</span>
              </>
            )}
            <span className="text-gray-300">|</span>
            <span>v{resume.version}</span>
            <span className="text-gray-300">|</span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor}`}>
              {resume.status}
            </span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {!resume.is_primary && resume.status === "parsed" && onSetPrimary && (
          <button
            onClick={() => onSetPrimary(resume.id)}
            className="rounded px-3 py-1.5 text-xs font-medium text-primary-600 hover:bg-primary-50"
          >
            Set Primary
          </button>
        )}
        {onView && (
          <button
            onClick={() => onView(resume.id)}
            className="rounded px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100"
          >
            View
          </button>
        )}
        {onDelete && (
          <button
            onClick={() => onDelete(resume.id)}
            className="rounded px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
