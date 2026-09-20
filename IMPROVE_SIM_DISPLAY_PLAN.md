# Plan: Improve Simulation Record Display

## Goal
Improve the what-if analysis UI across all simulation-related pages to clearly communicate that simulations are hypothetical analyses, not live hiring decisions. Standardize banners, add simulation record metadata, add data isolation indicators, and handle all status states.

## Gap Analysis (Current State vs Spec)

| Requirement | Details | Results | Ranking Impact | Requirement Impact |
|---|---|---|---|---|
| What-if banner | Has "Sandbox Scenario" warning (line 341) | Has "What-if analysis" banner (line 301) | Has "Read-only analysis" banner (line 351) | Has "What-if analysis" banner (line 237) |
| Simulation Record metadata | Partial: config version, created, updated, completed (line 306) | Missing | Missing | Missing |
| Data Isolation Indicator | Embedded in sandbox warning | Missing as distinct element | Missing | Missing |
| Baseline vs Sim separation | Grid layout (line 398) | SummaryCards with baseline/sim | N/A | N/A |
| Status state handling | ScenarioStatusBadge + inline badges | Execution status chips | Status-aware empty states | Status-aware empty states |
| Empty states | "No runs yet" (line 466) | "No results" / "No candidates match" | "No completed execution" (line 305) | "No candidates affected" (line 450) |
| Error states | Toast only | Toast only | Toast only | Toast only |

## Plan

### Step 1: Create `WhatIfBanner` Component
**File:** `frontend/src/components/simulations/WhatIfBanner.tsx`

Reusable banner component with consistent wording across all pages. Displays a prominent amber/yellow banner with the message: "What-if analysis — not a live hiring decision. No job data, applications, or rankings were created or modified by this simulation."

### Step 2: Create `SimulationRecordHeader` Component
**File:** `frontend/src/components/simulations/SimulationRecordHeader.tsx`

Displays the simulation record metadata section:
- Scenario ID (truncated)
- Scenario name
- Job title and company
- Status badge
- Created by and created date
- Config version
- Number of executions / last run date
- Baseline config version (from `baseline_config.job_version`)

Receives `scenario: SimulationScenario` and `executions: SimulationExecution[]` as props.

### Step 3: Create `DataIsolationIndicator` Component
**File:** `frontend/src/components/simulations/DataIsolationIndicator.tsx`

Small badge/chip that visually indicates data isolation: "Sandbox — isolated from live hiring". Uses a distinct color (e.g., teal/green border) to differentiate from the what-if banner.

### Step 4: Update `SimulationDetails.tsx`
- Replace the "Sandbox Scenario" warning (line 340-352) with `WhatIfBanner`
- Add `SimulationRecordHeader` below the page title, incorporating the existing metadata grid (line 306-331) into the new component
- Add `DataIsolationIndicator` next to the status badge
- Enhance the execution list status display to handle all 6 states explicitly (currently uses a generic fallback for non-completed/failed/cancelled)

### Step 5: Update `SimulationResults.tsx`
- Replace the "What-if analysis" banner (line 301-305) with `WhatIfBanner`
- Add `SimulationRecordHeader` below the page title
- Add `DataIsolationIndicator` next to the status badge

### Step 6: Update `SimulationRankingImpact.tsx`
- Replace the "Read-only analysis" banner (line 350-354) with `WhatIfBanner`
- Add `SimulationRecordHeader` below the page title
- Add `DataIsolationIndicator` next to the status badge

### Step 7: Update `SimulationRequirementImpact.tsx`
- Replace the "What-if analysis" banner (line 237-241) with `WhatIfBanner`
- Add `SimulationRecordHeader` below the page title
- Add `DataIsolationIndicator` next to the status badge

### Step 8: Run lint + typecheck
- Run `npx tsc --noEmit` to verify no TypeScript errors
- Verify the app still builds

## Files to Modify
- `frontend/src/components/simulations/WhatIfBanner.tsx` (new)
- `frontend/src/components/simulations/SimulationRecordHeader.tsx` (new)
- `frontend/src/components/simulations/DataIsolationIndicator.tsx` (new)
- `frontend/src/pages/recruiter/SimulationDetails.tsx`
- `frontend/src/pages/recruiter/SimulationResults.tsx`
- `frontend/src/pages/recruiter/SimulationRankingImpact.tsx`
- `frontend/src/pages/recruiter/SimulationRequirementImpact.tsx`

## Constraints
- Reuse existing UI components (Button, ScenarioStatusBadge, etc.)
- Additive only — no breaking changes to existing features
- All values from real backend data — no hardcoded/fake values
- Do not implement Phase 7+ functionality
