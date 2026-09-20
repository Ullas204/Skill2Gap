import type {
  FieldChangeKind,
  SimulationChangesResponse,
} from "../../types/simulations";

const KIND_STYLES: Record<FieldChangeKind, { badge: string; arrow: string }> = {
  unchanged: { badge: "bg-gray-100 text-gray-500", arrow: "=" },
  increased: { badge: "bg-green-100 text-green-700", arrow: "\u2191" },
  decreased: { badge: "bg-red-100 text-red-700", arrow: "\u2193" },
  added: { badge: "bg-green-100 text-green-700", arrow: "+" },
  removed: { badge: "bg-red-100 text-red-700", arrow: "\u2212" },
  changed: { badge: "bg-amber-100 text-amber-700", arrow: "~" },
};

function ChangeBadge({ change }: { change: FieldChangeKind }) {
  const style = KIND_STYLES[change] ?? KIND_STYLES.unchanged;
  if (change === "unchanged") return null;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${style.badge}`}>
      <span>{style.arrow}</span>
      {change}
    </span>
  );
}

function SkillChips({ skills, tone }: { skills: string[]; tone: "added" | "removed" }) {
  if (skills.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.map((skill) => (
        <span
          key={skill}
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
            tone === "added" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}
        >
          <span className="font-bold">{tone === "added" ? "+" : "\u2212"}</span>
          {skill}
        </span>
      ))}
    </div>
  );
}

interface ChangesSectionProps {
  changes: SimulationChangesResponse;
  title?: string;
}

export function ChangesSection({ changes, title = "Review changes" }: ChangesSectionProps) {
  const changedFields = changes.fields.filter((f) => f.change !== "unchanged");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
          <p className="mt-0.5 text-xs text-gray-500">
            Baseline vs proposed simulation configuration (config v{changes.config_version})
          </p>
        </div>
        {changes.total_changes > 0 ? (
          <span className="inline-flex rounded-full bg-primary-100 px-2.5 py-1 text-xs font-semibold text-primary-700">
            {changes.total_changes} change{changes.total_changes === 1 ? "" : "s"}
          </span>
        ) : (
          <span className="inline-flex rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-700">
            No changes
          </span>
        )}
      </div>

      {changes.total_changes === 0 ? (
        <p className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          The proposed configuration matches the baseline. Adjust the settings to create a
          &quot;what-if&quot; scenario.
        </p>
      ) : (
        <div className="space-y-3">
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-2">Setting</th>
                  <th className="px-4 py-2">Baseline</th>
                  <th className="px-4 py-2">Scenario</th>
                  <th className="px-4 py-2 text-right">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {changedFields.map((field) => (
                  <tr key={field.key}>
                    <td className="px-4 py-2 font-medium text-gray-900">{field.label}</td>
                    <td className="px-4 py-2 text-gray-600">
                      {formatValue(field.key, field.baseline)}
                    </td>
                    <td className="px-4 py-2 text-gray-900">{formatValue(field.key, field.scenario)}</td>
                    <td className="px-4 py-2 text-right">
                      <ChangeBadge change={field.change} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {(changedFields.some((f) => f.key.startsWith("requirements.")) ||
            changes.skills.moved.length > 0 ||
            changes.skills.mandatory_added.length > 0 ||
            changes.skills.preferred_added.length > 0 ||
            changes.skills.mandatory_removed.length > 0 ||
            changes.skills.preferred_removed.length > 0) && (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Skill requirements
              </h4>
              <div className="mt-3 space-y-3">
                <div>
                  <p className="mb-1 text-xs font-medium text-gray-500">Added</p>
                  {changes.skills.mandatory_added.length ||
                  changes.skills.preferred_added.length ? (
                    <SkillChips
                      skills={[...changes.skills.mandatory_added, ...changes.skills.preferred_added]}
                      tone="added"
                    />
                  ) : (
                    <p className="text-xs text-gray-400">None</p>
                  )}
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-gray-500">Removed</p>
                  {changes.skills.mandatory_removed.length ||
                  changes.skills.preferred_removed.length ? (
                    <SkillChips
                      skills={[
                        ...changes.skills.mandatory_removed,
                        ...changes.skills.preferred_removed,
                      ]}
                      tone="removed"
                    />
                  ) : (
                    <p className="text-xs text-gray-400">None</p>
                  )}
                </div>
                {changes.skills.moved.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-gray-500">Moved</p>
                    <div className="flex flex-wrap gap-1.5">
                      {changes.skills.moved.map((move) => (
                        <span
                          key={`${move.skill}-${move.from_list}-${move.to_list}`}
                          className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700"
                        >
                          {move.skill}: {move.from_list} &rarr; {move.to_list}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatValue(key: string, value: string | number | null): string {
  if (value === null || value === undefined) return "—";
  if (key.startsWith("scoring_weights.")) {
    return `${(Number(value) * 100).toFixed(0)}%`;
  }
  if (key === "threshold") return `${value}%`;
  if (typeof value === "number") return String(value);
  return value;
}