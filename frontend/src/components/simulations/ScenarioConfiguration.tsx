import { useState } from "react";
import type { KeyboardEvent } from "react";

import type {
  EducationRequirement,
  ExperienceRange,
  SimulationConfiguration,
  SimulationEducationLevel,
  SimulationEducationRequirement,
  SimulationRequirements,
  SimulationScoringWeights,
} from "../../types/simulations";
import {
  EDUCATION_LEVEL_LABELS,
  EDUCATION_LEVEL_OPTIONS,
  EDUCATION_REQUIREMENT_LABELS,
  EDUCATION_REQUIREMENT_OPTIONS,
  SCORING_WEIGHT_FIELDS,
  educationLabel,
  experienceLabel,
  scoringWeightsTotal,
  scoringWeightsTotalPercent,
} from "../../types/simulations";

function SkillTagEditor({
  tags,
  onChange,
  placeholder,
  disabled,
  moveLabel,
  onMove,
}: {
  tags: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
  disabled?: boolean;
  moveLabel?: string;
  onMove?: (tag: string) => void;
}) {
  const [text, setText] = useState("");

  function addTag() {
    const value = text.trim();
    if (!value) return;
    if (tags.includes(value)) {
      setText("");
      return;
    }
    onChange([...tags, value]);
    setText("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    } else if (e.key === "Backspace" && !text && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700"
        >
          {tag}
          {!disabled && onMove && moveLabel && (
            <button
              type="button"
              aria-label={`Move ${tag} to ${moveLabel}`}
              title={`Move to ${moveLabel}`}
              className="font-semibold text-primary-400 hover:text-primary-700"
              onClick={() => onMove(tag)}
            >
              &rarr;
            </button>
          )}
          {!disabled && (
            <button
              type="button"
              aria-label={`Remove ${tag}`}
              className="text-primary-400 hover:text-primary-600"
              onClick={() => onChange(tags.filter((t) => t !== tag))}
            >
              &times;
            </button>
          )}
        </span>
      ))}
      {!disabled && (
        <input
          value={text}
          placeholder={placeholder}
          className="min-w-[8rem] flex-1 border-none p-0 text-sm focus:outline-none focus:ring-0"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={addTag}
        />
      )}
    </div>
  );
}

interface ScenarioConfigurationProps {
  value: SimulationConfiguration;
  onChange: (next: SimulationConfiguration) => void;
  disabled?: boolean;
}

export function ScenarioConfiguration({ value, onChange, disabled }: ScenarioConfigurationProps) {
  const total = scoringWeightsTotal(value.scoring_weights);
  const totalPercent = scoringWeightsTotalPercent(value.scoring_weights);
  const weightsBalanced = Math.abs(total - 1) <= 0.001;

  function updateWeights(key: keyof SimulationScoringWeights, nextValue: number) {
    onChange({
      ...value,
      scoring_weights: { ...value.scoring_weights, [key]: nextValue },
    });
  }

  function updateRequirements(patch: Partial<SimulationRequirements>) {
    onChange({
      ...value,
      requirements: { ...value.requirements, ...patch },
    });
  }

  function updateExperience(patch: Partial<ExperienceRange>) {
    const current = value.requirements.experience ?? { minimum_years: null, maximum_years: null };
    updateRequirements({ experience: { ...current, ...patch } });
  }

  function updateEducation(patch: Partial<EducationRequirement>) {
    const current: EducationRequirement =
      value.requirements.education ?? { level: null, requirement: "required" };
    updateRequirements({ education: { ...current, ...patch } });
  }

  function normalizeYears(next: string): number | null {
    const parsed = Number(next);
    if (!next || Number.isNaN(parsed)) return null;
    return Math.min(50, Math.max(0, Math.round(parsed)));
  }

  function moveSkill(skill: string, from: "mandatory" | "preferred") {
    if (from === "mandatory") {
      updateRequirements({
        mandatory_skills: value.requirements.mandatory_skills.filter((s) => s !== skill),
        preferred_skills: [...value.requirements.preferred_skills, skill],
      });
    } else {
      updateRequirements({
        preferred_skills: value.requirements.preferred_skills.filter((s) => s !== skill),
        mandatory_skills: [...value.requirements.mandatory_skills, skill],
      });
    }
  }

  const inputClass =
    "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:bg-gray-50 disabled:text-gray-500";

  return (
    <div className="space-y-6">
      {/* Scoring strategy */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900">Scoring strategy</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Relative importance of each screening dimension. Weights are bounded to [0, 1] and must
          total 100%.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {SCORING_WEIGHT_FIELDS.map((field) => (
            <label key={field.key} className="block">
              <span className="text-sm text-gray-600">{field.label}</span>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={value.scoring_weights[field.key]}
                disabled={disabled}
                className={inputClass}
                onChange={(e) =>
                  updateWeights(field.key, Math.min(1, Math.max(0, Number(e.target.value) || 0)))
                }
              />
            </label>
          ))}
        </div>
        <div className="mt-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Total</span>
            <span
              className={
                weightsBalanced ? "font-semibold text-green-600" : "font-semibold text-red-600"
              }
            >
              {totalPercent}%
            </span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full rounded-full transition-all ${weightsBalanced ? "bg-green-500" : "bg-red-500"}`}
              style={{ width: `${Math.min(100, total * 100)}%` }}
            />
          </div>
          {!weightsBalanced && (
            <p className="mt-1 text-xs text-red-600">
              Weights must total 100% (currently {totalPercent}%). Adjust the weights to balance the
              strategy.
            </p>
          )}
        </div>
      </div>

      {/* Threshold & shortlist */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm text-gray-600">Minimum pass threshold ({value.threshold}%)</span>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={value.threshold}
            disabled={disabled}
            className="mt-2 w-full accent-primary-600"
            onChange={(e) => onChange({ ...value, threshold: Number(e.target.value) })}
          />
        </label>
        <label className="block">
          <span className="text-sm text-gray-600">Shortlist size</span>
          <input
            type="number"
            min={1}
            max={500}
            value={value.shortlist_size}
            disabled={disabled}
            className={inputClass}
            onChange={(e) =>
              onChange({
                ...value,
                shortlist_size: Math.min(500, Math.max(1, Number(e.target.value) || 1)),
              })
            }
          />
        </label>
      </div>

      {/* Skills */}
      <div className="space-y-3">
        <div>
          <span className="text-sm text-gray-600">Mandatory skills</span>
          <div className="mt-1">
            <SkillTagEditor
              tags={value.requirements.mandatory_skills}
              onChange={(tags) => updateRequirements({ mandatory_skills: tags })}
              placeholder="Add required skill + Enter"
              disabled={disabled}
              moveLabel="preferred"
              onMove={disabled ? undefined : (skill) => moveSkill(skill, "mandatory")}
            />
          </div>
        </div>
        <div>
          <span className="text-sm text-gray-600">Preferred skills</span>
          <div className="mt-1">
            <SkillTagEditor
              tags={value.requirements.preferred_skills}
              onChange={(tags) => updateRequirements({ preferred_skills: tags })}
              placeholder="Add preferred skill + Enter"
              disabled={disabled}
              moveLabel="mandatory"
              onMove={disabled ? undefined : (skill) => moveSkill(skill, "preferred")}
            />
          </div>
        </div>
        <p className="text-xs text-gray-400">
          Use the arrow on a skill chip to move it between the mandatory and preferred lists.
        </p>
      </div>

      {/* Experience range */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900">Experience range</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Years of experience candidates must have. Leave a bound empty for &quot;no constraint&quot;
          on that side.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-sm text-gray-600">Minimum years</span>
            <input
              type="number"
              min={0}
              max={50}
              value={value.requirements.experience?.minimum_years ?? ""}
              disabled={disabled}
              className={inputClass}
              onChange={(e) => updateExperience({ minimum_years: normalizeYears(e.target.value) })}
            />
          </label>
          <label className="block">
            <span className="text-sm text-gray-600">Maximum years</span>
            <input
              type="number"
              min={0}
              max={50}
              value={value.requirements.experience?.maximum_years ?? ""}
              disabled={disabled}
              className={inputClass}
              onChange={(e) => updateExperience({ maximum_years: normalizeYears(e.target.value) })}
            />
          </label>
        </div>
      </div>

      {/* Education */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900">Education</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Highest education level and how strictly it applies.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm text-gray-600">Education level</span>
            <select
              value={value.requirements.education?.level ?? ""}
              disabled={disabled}
              className={inputClass}
              onChange={(e) =>
                updateEducation({
                  level: (e.target.value || null) as SimulationEducationLevel | null,
                })
              }
            >
              <option value="">Any level</option>
              {EDUCATION_LEVEL_OPTIONS.map((level) => (
                <option key={level} value={level}>
                  {EDUCATION_LEVEL_LABELS[level]}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm text-gray-600">Requirement</span>
            <select
              value={
                value.requirements.education?.requirement ??
                ("required" as SimulationEducationRequirement)
              }
              disabled={disabled}
              className={inputClass}
              onChange={(e) =>
                updateEducation({
                  requirement: e.target.value as SimulationEducationRequirement,
                })
              }
            >
              {EDUCATION_REQUIREMENT_OPTIONS.map((requirement) => (
                <option key={requirement} value={requirement}>
                  {EDUCATION_REQUIREMENT_LABELS[requirement]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </div>
  );
}

export function SimulationConfigSummary({ config }: { config: SimulationConfiguration | null }) {
  if (!config) {
    return <p className="text-sm text-gray-500">No simulation configuration recorded.</p>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Scoring weights</h4>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
          {SCORING_WEIGHT_FIELDS.map((dim) => (
            <div key={dim.key} className="flex items-center justify-between border-b border-gray-100 py-1">
              <dt className="text-sm text-gray-600">{dim.label}</dt>
              <dd className="text-sm font-medium text-gray-900">
                {(config.scoring_weights[dim.key] * 100).toFixed(0)}%
              </dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Pass threshold</h4>
          <p className="mt-1 text-sm font-medium text-gray-900">{config.threshold}%</p>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Shortlist size</h4>
          <p className="mt-1 text-sm font-medium text-gray-900">{config.shortlist_size}</p>
        </div>
      </div>
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Requirements</h4>
        <dl className="mt-2 space-y-2 text-sm">
          <div className="flex gap-2">
            <dt className="w-36 shrink-0 text-gray-500">Mandatory skills</dt>
            <dd className="text-gray-900">
              {config.requirements.mandatory_skills.length > 0
                ? config.requirements.mandatory_skills.join(", ")
                : "—"}
            </dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-36 shrink-0 text-gray-500">Preferred skills</dt>
            <dd className="text-gray-900">
              {config.requirements.preferred_skills.length > 0
                ? config.requirements.preferred_skills.join(", ")
                : "—"}
            </dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-36 shrink-0 text-gray-500">Experience</dt>
            <dd className="text-gray-900">{experienceLabel(config.requirements)}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-36 shrink-0 text-gray-500">Education</dt>
            <dd className="text-gray-900">{educationLabel(config.requirements)}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}