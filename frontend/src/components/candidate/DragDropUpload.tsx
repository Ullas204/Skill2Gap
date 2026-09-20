import { useCallback, useRef, useState } from "react";

interface DragDropUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number;
  disabled?: boolean;
}

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "text/plain",
  "text/html",
  "application/rtf",
];

export function DragDropUpload({
  onFileSelect,
  accept = ".pdf,.docx,.doc,.txt,.html,.htm,.rtf",
  maxSize = 10 * 1024 * 1024,
  disabled = false,
}: DragDropUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): string | null => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      const allowed = accept.split(",").map((a) => a.trim().toLowerCase());
      if (!allowed.includes(ext) && !ALLOWED_TYPES.includes(file.type)) {
        return "Unsupported file type. Accepted: PDF, DOCX, DOC, TXT, HTML, RTF";
      }
      if (file.size > maxSize) {
        return `File too large. Maximum size is ${maxSize / (1024 * 1024)} MB`;
      }
      if (file.size === 0) {
        return "File is empty";
      }
      return null;
    },
    [accept, maxSize],
  );

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      onFileSelect(file);
    },
    [validateFile, onFileSelect],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [disabled, handleFile],
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!disabled) setDragOver(true);
    },
    [disabled],
  );

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  return (
    <div className="w-full">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        className={`relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
          dragOver
            ? "border-primary-500 bg-primary-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100"
        } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
      >
        <svg className="mb-3 h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="mb-1 text-sm font-medium text-gray-700">
          {dragOver ? "Drop your resume here" : "Drag & drop your resume, or click to browse"}
        </p>
        <p className="text-xs text-gray-500">
          PDF, DOCX, DOC, TXT, HTML, RTF (max {maxSize / (1024 * 1024)} MB)
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled}
        />
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
