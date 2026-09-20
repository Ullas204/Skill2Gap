import { describe, it, expect } from "vitest";

import {
  computeClientChanges,
  createDefaultSimulationConfiguration,
  educationLabel,
  experienceLabel,
  scoringWeightsTotal,
  scoringWeightsTotalPercent,
  simulationConfigFromBaseline,
  validateSimulationConfig,
  type SimulationBaselineConfig,
  type SimulationConfiguration,
} from "./simulations";

const baseline: SimulationBaselineConfig = {
  source: "job_post",
  job_id: "job-1",
  job_version: 1,
  title: "Senior Engineer",
  company: "Acme",
  scoring_weights: {
    skills: 0.4,
    experience: 0.25,
    education: 0.15,
    projects: 0.2,
    certifications: 0,
    location: 0,
    employment_type: 0,
    semantic: 0,
  },
  threshold: 70,
  shortlist_size: 10,
  requirements: {
    mandatory_skills: ["React", "TypeScript"],
    preferred_skills: ["GraphQL"],
    experience_required: "3+ years in web development",
    education_required: "Bachelor's degree",
  },
};

function makeConfig(overrides: Partial<SimulationConfiguration>): SimulationConfiguration {
  const defaults = createDefaultSimulationConfiguration();
  return {
    ...defaults,
    requirements: {
      ...defaults.requirements,
      mandatory_skills: ["React", "TypeScript"],
      preferred_skills: ["GraphQL"],
    },
    ...overrides,
  };
}

describe("scoringWeightsTotal", () => {
  it("sums all weight dimensions", () => {
    const config = makeConfig({});
    expect(scoringWeightsTotal(config.scoring_weights)).toBeCloseTo(1);
  });

  it("reports totals as percentages", () => {
    expect(scoringWeightsTotalPercent(baseline.scoring_weights)).toBe(100);
    const over = { ...baseline.scoring_weights, skills: 0.5 };
    expect(scoringWeightsTotalPercent(over)).toBe(110);
  });
});

describe("validateSimulationConfig", () => {
  it("returns actions for a missing config", () => {
    const result = validateSimulationConfig(null);
    expect(result.valid).toBe(false);
    expect(result.errors[0].field).toBe("config");
  });

  it("accepts a well-formed configuration", () => {
    const result = validateSimulationConfig(makeConfig({}));
    expect(result.valid).toBe(true);
    expect(result.errors).toEqual([]);
  });

  it("rejects weights that do not total 100%", () => {
    const config = makeConfig({
      scoring_weights: {
        skills: 0.5,
        experience: 0.25,
        education: 0.15,
        projects: 0.2,
        certifications: 0,
        location: 0,
        employment_type: 0,
        semantic: 0,
      },
    });
    const result = validateSimulationConfig(config);
    expect(result.valid).toBe(false);
    expect(result.errors.find((e) => e.field === "scoring_weights.total")).toBeDefined();
    expect(result.errors[0].message).toContain("total 100%");
  });

  it("rejects out-of-range threshold and shortlist", () => {
    const config = makeConfig({ threshold: 101, shortlist_size: 0 });
    const result = validateSimulationConfig(config);
    expect(result.errors.map((e) => e.field)).toContain("threshold");
    expect(result.errors.map((e) => e.field)).toContain("shortlist_size");
  });

  it("rejects duplicated and overlapping skills", () => {
    const dupe = makeConfig({
      requirements: { ...makeConfig({}).requirements, mandatory_skills: ["React", "react"] },
    });
    expect(validateSimulationConfig(dupe).valid).toBe(false);

    const overlap = makeConfig({
      requirements: {
        ...makeConfig({}).requirements,
        mandatory_skills: ["React"],
        preferred_skills: [" react "],
      },
    });
    const result = validateSimulationConfig(overlap);
    expect(result.valid).toBe(false);
    expect(result.errors.find((e) => e.message.includes("both mandatory and preferred"))).toBeDefined();
  });

  it("rejects an empty experience range and inverted bounds", () => {
    const empty = makeConfig({
      requirements: { ...makeConfig({}).requirements, experience: { minimum_years: null, maximum_years: null } },
    });
    expect(validateSimulationConfig(empty).errors[0].field).toBe("requirements.experience");

    const inverted = makeConfig({
      requirements: { ...makeConfig({}).requirements, experience: { minimum_years: 5, maximum_years: 2 } },
    });
    const result = validateSimulationConfig(inverted);
    expect(result.valid).toBe(false);
    expect(result.errors.find((e) => e.message.includes("cannot be lower"))).toBeDefined();
  });

  it("rejects an unknown education level", () => {
    const config = makeConfig({
      requirements: {
        ...makeConfig({}).requirements,
        education: { level: "phd" as any, requirement: "required" },
      },
    });
    const result = validateSimulationConfig(config);
    expect(result.valid).toBe(false);
    expect(result.errors.find((e) => e.field === "requirements.education.level")).toBeDefined();
  });
});

describe("experienceLabel / educationLabel", () => {
  it("formats structured ranges and falls back to legacy text", () => {
    expect(experienceLabel({ ...makeConfig({}).requirements, experience: { minimum_years: 3, maximum_years: 5 } })).toBe(
      "3–5 years",
    );
    expect(experienceLabel({ ...makeConfig({}).requirements, experience: { minimum_years: 3, maximum_years: null } })).toBe(
      "3+ years",
    );
    expect(experienceLabel({ ...makeConfig({}).requirements, experience_required: "2+ years" })).toBe("2+ years");
    expect(experienceLabel({ ...makeConfig({}).requirements })).toBe("—");
  });

  it("formats education with requirement detail", () => {
    expect(
      educationLabel({ ...makeConfig({}).requirements, education: { level: "master", requirement: "preferred" } }),
    ).toBe("Master's (Preferred)");
    expect(
      educationLabel({ ...makeConfig({}).requirements, education: { level: "bachelor", requirement: "required" } }),
    ).toBe("Bachelor's");
    expect(educationLabel({ ...makeConfig({}).requirements, education: { level: null, requirement: "optional" } })).toBe(
      "Any level",
    );
    expect(educationLabel({ ...makeConfig({}).requirements, education_required: "Degree" })).toBe("Degree");
  });
});

function weightConfig(weights: Partial<SimulationBaselineConfig["scoring_weights"]>): SimulationConfiguration {
  return {
    ...createDefaultSimulationConfiguration(),
    version: 2,
    scoring_weights: { ...baseline.scoring_weights, ...weights },
    threshold: baseline.threshold,
    shortlist_size: baseline.shortlist_size,
    requirements: { ...createDefaultSimulationConfiguration().requirements, mandatory_skills: ["React", "Go"] },
  };
}

describe("simulationConfigFromBaseline", () => {
  it("seeds an editable config from a frozen baseline", () => {
    const config = simulationConfigFromBaseline(baseline);
    expect(config.version).toBe(1);
    expect(config.scoring_weights).toEqual(baseline.scoring_weights);
    expect(config.requirements.mandatory_skills).toEqual(["React", "TypeScript"]);
    expect(config.requirements.experience).toBeNull();
  });
});

describe("computeClientChanges", () => {
  it("detects weight, threshold and shortlist differences", () => {
    const config = weightConfig({ skills: 0.45, semantic: 0.05 });
    config.threshold = 75;
    config.shortlist_size = 15;
    const changes = computeClientChanges(baseline, config);

    expect(changes.fields.find((f) => f.key === "threshold")?.change).toBe("increased");
    expect(changes.fields.find((f) => f.key === "shortlist_size")?.change).toBe("increased");
    expect(changes.fields.find((f) => f.key === "scoring_weights.skills")?.change).toBe("increased");
    expect(changes.fields.find((f) => f.key === "scoring_weights.semantic")?.change).toBe("increased");
    expect(changes.fields.find((f) => f.key === "scoring_weights.education")?.change).toBe("unchanged");
  });

  it("classifies decreased numeric fields", () => {
    const config = weightConfig({});
    config.threshold = 60;
    const changes = computeClientChanges(baseline, config);
    expect(changes.fields.find((f) => f.key === "threshold")?.change).toBe("decreased");
  });

  it("detects added, removed and moved skills", () => {
    const config = makeConfig({
      requirements: {
        mandatory_skills: ["React", "Go"],
        preferred_skills: ["TypeScript"],
      },
    });
    const changes = computeClientChanges(baseline, config);

    expect(changes.skills.mandatory_added).toEqual(["go"]);
    expect(changes.skills.mandatory_removed).toEqual([]);
    expect(changes.skills.preferred_added).toEqual([]);
    expect(changes.skills.preferred_removed).toEqual(["graphql"]);
    expect(changes.skills.moved).toEqual([
      { skill: "typescript", from_list: "mandatory", to_list: "preferred" },
    ]);
    expect(changes.total_changes).toBeGreaterThan(0);
  });

  it("returns no changes for an identical configuration", () => {
    const config = simulationConfigFromBaseline(baseline);
    config.requirements.experience = { minimum_years: null, maximum_years: null };
    const changes = computeClientChanges(baseline, {
      ...config,
      requirements: { ...baseline.requirements, experience: null, education: null },
    });
    expect(changes.total_changes).toBe(0);
    expect(changes.fields.every((f) => f.change === "unchanged")).toBe(true);
  });
});