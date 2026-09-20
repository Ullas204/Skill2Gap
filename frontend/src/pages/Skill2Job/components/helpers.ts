export function extractErrorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(extractErrorMessage).join("; ");
  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>;
    if (d.detail) return extractErrorMessage(d.detail);
    if (d.message) return String(d.message);
    if (d.error) return extractErrorMessage(d.error);
  }
  return "An unexpected error occurred";
}

export function priorityColor(p: string): string {
  switch (p.toLowerCase()) {
    case "critical":
    case "high":
      return "bg-red-100 text-red-700 border border-red-200";
    case "medium":
      return "bg-amber-100 text-amber-700 border border-amber-200";
    case "low":
      return "bg-green-100 text-green-700 border border-green-200";
    default:
      return "bg-gray-100 text-gray-600 border border-gray-200";
  }
}

export function formatRecommendation(r: string): string {
  return r
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
