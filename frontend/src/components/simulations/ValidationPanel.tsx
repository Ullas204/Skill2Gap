import type { SimulationValidationResponse } from "../../types/simulations";

function sectionLabel(field: string): string {
  if (field.startsWith("scoring_weights")) return "Scoring weights";
  if (field.startsWith("requirements")) return "Requirements";
  if (field === "threshold") return "Pass threshold";
  if (field === "shortlist_size") return "Shortlist size";
  return "Configuration";
}

interface ValidationPanelProps {
  validation: SimulationValidationResponse | null;
  loading?: boolean;
}

export function ValidationPanel({ validation, loading }: ValidationPanelProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-500">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" />
        Validating configuration…
      </div>
    );
  }

  if (!validation) return null;

  if (validation.valid) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
        <span className="mt-0.5 text-base leading-none font-bold">&#10003;</span>
        <div>
          <p className="font-semibold">Configuration is valid</p>
          <p className="mt-0.5 text-xs text-green-700">
            The scenario can be promoted to <span className="font-semibold">ready</span>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <p className="font-semibold">
        Configuration needs attention ({validation.errors.length} issue
        {validation.errors.length === 1 ? "" : "s"})
      </p>
      <ul className="mt-2 space-y-1.5">
        {validation.errors.map((issue, index) => (
          <li key={`${issue.field}-${index}`} className="flex items-start gap-2">
            <span className="mt-0.5 text-red-400">&#8226;</span>
            <span>
              <span className="mr-1.5 inline-flex rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700">
                {sectionLabel(issue.field)}
              </span>
              {issue.message}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}