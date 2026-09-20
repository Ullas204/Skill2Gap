import type {
  RequirementChangeDetail,
  RequirementChangeType,
  ImpactCategory,
} from "../../types/requirementImpact";
import {
  CHANGE_TYPE_LABELS,
  CHANGE_TYPE_COLORS,
  IMPACT_CATEGORY_LABELS,
  IMPACT_CATEGORY_COLORS,
} from "../../types/requirementImpact";

interface RequirementImpactTableProps {
  requirements: RequirementChangeDetail[];
  onSelect?: (requirement: RequirementChangeDetail) => void;
}

function ChangeTypeBadge({ type }: { type: RequirementChangeType }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${CHANGE_TYPE_COLORS[type]}`}
    >
      {CHANGE_TYPE_LABELS[type]}
    </span>
  );
}

function ImpactBadge({ category }: { category: ImpactCategory }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${IMPACT_CATEGORY_COLORS[category]}`}
    >
      {IMPACT_CATEGORY_LABELS[category]}
    </span>
  );
}

function RequirementTypeIcon({ type }: { type: string }) {
  switch (type) {
    case "skill":
      return (
        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437 1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008Z" />
        </svg>
      );
    case "experience":
      return (
        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
        </svg>
      );
    case "education":
      return (
        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5" />
        </svg>
      );
    default:
      return null;
  }
}

export function RequirementImpactTable({ requirements, onSelect }: RequirementImpactTableProps) {
  if (requirements.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <p className="text-sm text-gray-500">No requirement changes detected.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <div className="border-b border-gray-200 bg-gray-50 px-5 py-3">
        <h3 className="text-sm font-semibold text-gray-900">Requirement Changes</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          {requirements.length} requirement(s) changed between baseline and simulation.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Requirement
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Type
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Change
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Before
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                After
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                Affected
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                Newly Disqualified
              </th>
              <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                Avg Score Impact
              </th>
              <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                Impact
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {requirements.map((req, idx) => (
              <tr
                key={`${req.requirement_type}-${req.requirement_name}-${idx}`}
                className={`hover:bg-gray-50 ${onSelect ? "cursor-pointer" : ""}`}
                onClick={() => onSelect?.(req)}
              >
                <td className="whitespace-nowrap px-5 py-4">
                  <div className="flex items-center gap-3">
                    <RequirementTypeIcon type={req.requirement_type} />
                    <div>
                      <div className="text-sm font-medium text-gray-900">{req.requirement_name}</div>
                      <div className="text-xs text-gray-500 capitalize">{req.requirement_type}</div>
                    </div>
                  </div>
                </td>
                <td className="whitespace-nowrap px-5 py-4">
                  <span className="text-sm text-gray-600 capitalize">{req.requirement_type}</span>
                </td>
                <td className="whitespace-nowrap px-5 py-4">
                  <ChangeTypeBadge type={req.change_type} />
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-sm text-gray-600">
                  {req.baseline_value}
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-sm text-gray-900 font-medium">
                  {req.simulation_value}
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-right">
                  <span className="text-sm font-semibold text-gray-900">
                    {req.affected_candidates}
                  </span>
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-right">
                  <span
                    className={`text-sm font-semibold ${
                      req.newly_disqualified > 0 ? "text-red-600" : "text-gray-500"
                    }`}
                  >
                    {req.newly_disqualified}
                  </span>
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-right">
                  <span
                    className={`text-sm font-medium ${
                      req.avg_score_impact > 0
                        ? "text-green-600"
                        : req.avg_score_impact < 0
                          ? "text-red-600"
                          : "text-gray-500"
                    }`}
                  >
                    {req.avg_score_impact > 0 ? "+" : ""}
                    {req.avg_score_impact.toFixed(1)}
                  </span>
                </td>
                <td className="whitespace-nowrap px-5 py-4">
                  <ImpactBadge category={req.impact_category} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
