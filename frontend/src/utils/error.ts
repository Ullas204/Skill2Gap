import type { AxiosError } from "axios";

interface ServerError {
  detail?: string | Array<{ msg?: string; detail?: string }>;
  code?: string;
}

export function getErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === "object" && "isAxiosError" in err) {
    const axiosErr = err as AxiosError<ServerError>;
    const detail = axiosErr.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((e) => e.msg || e.detail || "").join(", ");
    }
  }
  if (err instanceof Error) return err.message;
  return fallback;
}
