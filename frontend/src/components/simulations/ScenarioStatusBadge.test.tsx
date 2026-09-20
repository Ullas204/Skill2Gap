import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScenarioStatusBadge } from "./ScenarioStatusBadge";

describe("ScenarioStatusBadge", () => {
  it("renders the status label in a humanized form", () => {
    render(<ScenarioStatusBadge status="ready" />);
    expect(screen.getByText("ready")).toBeInTheDocument();
  });

  it("humanizes underscore-separated statuses", () => {
    render(<ScenarioStatusBadge status="queued_for_run" />);
    expect(screen.getByText("queued for run")).toBeInTheDocument();
  });

  it.each([
    ["draft", "bg-yellow-100"],
    ["ready", "bg-blue-100"],
    ["completed", "bg-green-100"],
    ["failed", "bg-red-100"],
  ])("styles %s with the matching palette", (status, expectedClass) => {
    const { container } = render(<ScenarioStatusBadge status={status} />);
    expect(container.querySelector("span")?.className).toContain(expectedClass);
  });
});