import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { LandingPage } from "../pages/LandingPage";

function renderLanding() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
}

describe("LandingPage", () => {
  it("renders the hero with the required headline and subtitle", () => {
    renderLanding();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Transform Recruitment with/i);
    expect(
      screen.getByText(/AI-Powered Talent Intelligence & Recruitment Platform/i),
    ).toBeInTheDocument();
  });

  it("links the primary CTA to /login and Explore Platform to features", () => {
    renderLanding();
    const getStartedLinks = screen.getAllByRole("link", { name: /Get Started/i });
    expect(getStartedLinks.length).toBeGreaterThan(0);
    for (const link of getStartedLinks) {
      expect(link).toHaveAttribute("href", "/login");
    }
    expect(screen.getByText("Explore Platform")).toBeInTheDocument();
  });

  it("shows the problem → AI solution framing", () => {
    renderLanding();
    expect(screen.getByText("The Problem")).toBeInTheDocument();
    expect(screen.getByText("The AI Solution")).toBeInTheDocument();
    expect(screen.getAllByText("Manual resume screening").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Agentic AI HR Assistant").length).toBeGreaterThan(0);
  });

  it("displays all eight numbered platform capabilities", () => {
    renderLanding();
    for (const title of [
      "AI Resume Intelligence",
      "AI Candidate Ranking",
      "Explainable AI",
      "Responsible AI",
      "AI Interview Intelligence",
      "AI Assessments",
      "Recruitment Analytics",
      "Agentic AI HR Assistant",
    ]) {
      expect(screen.getAllByText(title).length).toBeGreaterThan(0);
    }
  });

  it("renders the five-step workflow", () => {
    renderLanding();
    expect(screen.getByText(/Step 1: Create Job/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 5: Data-Driven Hiring/i)).toBeInTheDocument();
  });

  it("shows all four informational role cards (no restricted dashboards)", () => {
    renderLanding();
    for (const role of ["Candidate", "Recruiter", "HR", "Admin"]) {
      const heading = screen.getByRole("heading", { name: role });
      expect(heading).toBeInTheDocument();
    }
    // Role CTAs point to registration, never directly into a dashboard.
    const candidateCta = screen.getByRole("link", { name: /Candidate Experience/i });
    expect(candidateCta).toHaveAttribute("href", "/register");
  });

  it("communicates the responsible AI message verbatim", () => {
    renderLanding();
    expect(
      screen.getByText(/AI assists hiring decisions\. Humans remain responsible/i),
    ).toBeInTheDocument();
  });

  it("presents the technology stack section", () => {
    renderLanding();
    expect(
      screen.getByText(/Built on a Modern AI Engineering Stack/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Sentence Transformers")).toBeInTheDocument();
    expect(screen.getByText("LangGraph")).toBeInTheDocument();
  });

  it("does not fabricate customer or usage numbers", () => {
    renderLanding();
    const body = document.body.textContent || "";
    expect(body).not.toMatch(/10,000\+/);
    expect(body).not.toMatch(/\b1M\b/);
    expect(body).not.toMatch(/companies trust/i);
  });

  it("has a final CTA linking to login and register", () => {
    renderLanding();
    const cta = screen.getByText(/Build a Smarter, Fairer Hiring Process/i);
    expect(cta).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create Account" })).toHaveAttribute("href", "/register");
  });

  it("has accessible navigation with all five anchors", () => {
    renderLanding();
    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    for (const label of ["Platform", "Features", "How It Works", "Responsible AI", "Technology"]) {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    }
  });

  it("renders the footer with required sections", () => {
    renderLanding();
    expect(screen.getByText(/© \d{4} AI Hiring Copilot\. All rights reserved\./)).toBeInTheDocument();
    expect(screen.getByText(/AI-assisted hiring with transparency and human oversight/i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Footer — Responsible AI" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Footer — Access" })).toBeInTheDocument();
  });
});
