const STATUS_STYLES: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-800",
  ready: "bg-blue-100 text-blue-800",
  queued: "bg-indigo-100 text-indigo-800",
  running: "bg-purple-100 text-purple-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

export function ScenarioStatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-800";
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${style}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}