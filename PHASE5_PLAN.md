# Phase 5 — What-If Requirement Simulation: Implementation Plan

## Executive Summary

Phase 5 adds requirement-specific impact analysis on top of the existing Phase 3 (Simulation Engine) and Phase 4 (Ranking Impact Analyzer). The core insight: Phase 3 already evaluates candidates against baseline and simulation configs, and Phase 4 already analyzes ranking impact. Phase 5 **decomposes** that impact by individual requirement changes — answering "WHICH requirement changes caused those differences?"

**No new database models needed.** All Phase 5 analysis is computed from existing persisted data (configuration snapshots in `execution.configuration_snapshot` and dimension scores in `SimulationResult.baseline_dimensions`/`simulation_dimensions`).

---

## Architecture

```
Phase 3 Execution (already exists)
  └─ evaluation.evaluate_configuration() → baseline_dims + simulation_dims per candidate
  └─ SimulationResult persisted with baseline/simulation dimensions

Phase 4 RankingImpactAnalyzer (already exists)
  └─ Reads SimulationResult rows → ranking impact metrics

Phase 5 RequirementImpactAnalyzer (NEW)
  └─ Reads configuration_snapshot → identifies requirement changes
  └─ Reads SimulationResult dimensions → candidate satisfaction per requirement
  └─ Computes requirement-specific impact metrics
  └─ Provides deterministic attribution
```

---

## Files to Create

### Backend

| # | File | Purpose |
|---|------|---------|
| 1 | `backend/app/domain/requirement_impact_schemas.py` | Pydantic response schemas |
| 2 | `backend/app/services/simulation/requirement_impact_analyzer.py` | Core analysis engine |
| 3 | `backend/tests/test_simulation_phase5.py` | Unit + integration tests |

### Frontend

| # | File | Purpose |
|---|------|---------|
| 4 | `frontend/src/types/requirementImpact.ts` | TypeScript types |
| 5 | `frontend/src/pages/recruiter/SimulationRequirementImpact.tsx` | Requirement Impact page |
| 6 | `frontend/src/components/simulations/RequirementImpactTable.tsx` | Requirement impact table |
| 7 | `frontend/src/components/simulations/CandidateRequirementDetail.tsx` | Candidate detail drawer |

### Files to Modify

| # | File | Change |
|---|------|--------|
| 8 | `backend/app/api/v1/simulations.py` | Add 4 new API endpoints |
| 9 | `frontend/src/api/simulations.ts` | Add 4 new API methods |
| 10 | `frontend/src/App.tsx` | Add route for new page |
| 11 | `frontend/src/pages/recruiter/SimulationDetails.tsx` | Add "Requirement Impact" nav button |
| 12 | `backend/app/domain/enums.py` | Add `REQUIREMENT_IMPACT_VIEWED` audit event |

---

## Detailed Implementation

### Step 1: Backend Schemas (`requirement_impact_schemas.py`)

```python
# Key schemas:

class RequirementChangeDetail:
    """One changed requirement with its type and before/after values."""
    requirement_type: str          # "skill" | "experience" | "education"
    requirement_name: str          # "Docker", "experience", "education"
    change_type: str               # "added" | "removed" | "promoted" | "demoted" | "modified"
    baseline_value: str            # "preferred", "2+ years", "Bachelor's"
    simulation_value: str          # "mandatory", "4+ years", "Master's"
    affected_candidates: int       # candidates whose satisfaction changed
    newly_disqualified: int        # candidates who became not qualified due to this change
    newly_qualified: int           # candidates who became qualified due to this change
    avg_score_impact: float        # average score change for affected candidates

class CandidateRequirementImpact:
    """Per-candidate requirement satisfaction change."""
    candidate_id: UUID
    candidate_name: str
    affected_requirements: list[ChangedRequirementStatus]
    baseline_score: int
    simulation_score: int
    score_change: int
    baseline_rank: int
    simulation_rank: int
    rank_change: int
    baseline_qualified: bool
    simulation_qualified: bool
    qualification_change: str
    shortlist_change: str

class ChangedRequirementStatus:
    """One requirement's satisfaction change for a candidate."""
    requirement_type: str
    requirement_name: str
    baseline_satisfied: bool
    simulation_satisfied: bool
    baseline_status: str           # "SATISFIED" | "MISSING" | "NOT_APPLICABLE"
    simulation_status: str

class RequirementImpactResponse:
    """Full requirement impact analysis response."""
    simulation_id: UUID
    execution_id: UUID
    scenario_name: str
    job_title: str
    # Summary
    total_requirements_changed: int
    skills_added: int
    skills_removed: int
    skills_promoted: int
    skills_demoted: int
    experience_changed: bool
    education_changed: bool
    # Impact summary
    candidates_affected: int
    candidates_newly_qualified: int
    candidates_newly_disqualified: int
    candidates_score_changed: int
    candidates_rank_changed: int
    # Requirement details
    requirement_changes: list[RequirementChangeDetail]
    # Candidate details (paginated)
    affected_candidates: list[CandidateRequirementImpact]
```

### Step 2: Requirement Impact Analyzer (`requirement_impact_analyzer.py`)

**Architecture:**
```
RequirementImpactAnalyzer
├── analyze() → RequirementImpactResponse
├── get_requirement_list() → paginated requirement changes
├── get_affected_candidates() → paginated affected candidates
├── get_candidate_detail() → single candidate requirement detail
│
├── _identify_requirement_changes() → list[RequirementChangeDetail]
│   ├── _diff_skills() → skill changes (reuse change_detection semantics)
│   ├── _diff_experience() → experience changes
│   └── _diff_education() → education changes
│
├── _evaluate_candidate_satisfaction() → per-candidate satisfaction
│   ├── _check_skill_satisfaction() → uses MatchingEngine.skill_matches()
│   ├── _check_experience_satisfaction() → uses evaluation._experience_score_from_range()
│   └── _check_education_satisfaction() → uses evaluation._max_degree_rank()
│
└── _compute_requirement_impact() → aggregate metrics per requirement
```

**Key design decisions:**
1. Uses `MatchingEngine.skill_matches()` for skill satisfaction (same as production)
2. Uses `evaluation._experience_score_from_range()` for experience satisfaction
3. Uses `evaluation._max_degree_rank()` + `EDUCATION_LEVEL_RANK` for education satisfaction
4. Attribution is deterministic and rule-based (no ML explainability)
5. Reads from `execution.configuration_snapshot` for config comparison
6. Reads from `SimulationResult.baseline_dimensions`/`simulation_dimensions` for score attribution

**How satisfaction is determined:**
- For each requirement change, compare baseline vs simulation config
- For each candidate in SimulationResult:
  - Check if the candidate satisfies the baseline requirement (using MatchingEngine)
  - Check if the candidate satisfies the simulation requirement (using MatchingEngine)
  - If satisfaction status changed → candidate is "affected" by this requirement change

**How score impact is attributed:**
- Skill changes → attribute to `skill` dimension delta (from baseline_dimensions/simulation_dimensions)
- Experience changes → attribute to `experience` dimension delta
- Education changes → attribute to `education` dimension delta
- If multiple requirements in the same dimension changed → split proportionally

### Step 3: API Endpoints

Add to `simulations.py`:

```python
# Phase 5: Requirement Impact Analysis

GET /{simulation_id}/requirement-impact
    → RequirementImpactResponse
    Query params: execution_id (optional)

GET /{simulation_id}/requirement-impact/requirements
    → RequirementImpactListResponse (paginated)

GET /{simulation_id}/requirement-impact/candidates
    → RequirementImpactCandidateListResponse (paginated, filterable)
    Query params: requirement, requirement_type, impact, newly_qualified,
                  newly_disqualified, page, page_size, sort_by, order

GET /{simulation_id}/requirement-impact/candidates/{candidate_id}
    → CandidateRequirementImpactDetailResponse
```

All endpoints enforce:
- Authentication
- RBAC (admin, hr, recruiter)
- Organization isolation
- Execution status check (COMPLETED only)
- Audit logging

### Step 4: Frontend Types (`requirementImpact.ts`)

Mirror backend schemas as TypeScript interfaces.

### Step 5: Frontend API Methods

Add to `simulations.ts`:
```typescript
getRequirementImpact: (simulationId, executionId?) => ...
getRequirementImpactRequirements: (simulationId, params?) => ...
getRequirementImpactCandidates: (simulationId, params?) => ...
getCandidateRequirementDetail: (simulationId, candidateId, executionId?) => ...
```

### Step 6: Frontend Page (`SimulationRequirementImpact.tsx`)

Layout:
1. **Header**: Scenario name, status badge, execution info
2. **Requirement Changes Summary**: Cards showing added/removed/promoted/demoted counts
3. **Impact Summary**: Cards showing affected/qualified/disqualified counts
4. **Requirement Impact Table**: Each changed requirement with before→after and impact metrics
5. **Affected Candidates Table**: Paginated, filterable, sortable candidate list
6. **Candidate Detail Drawer**: Click a candidate to see per-requirement breakdown

### Step 7: Frontend Navigation

Add to `SimulationDetails.tsx` execution row buttons:
```tsx
<Button onClick={() => navigate(`/recruiter/simulations/${scenario.id}/requirement-impact`)}>
  Requirement Impact
</Button>
```

Add route in `App.tsx`:
```tsx
<Route path="/recruiter/simulations/:simulationId/requirement-impact"
       element={<ProtectedRoute roles={RECRUITER}><SimulationRequirementImpact /></ProtectedRoute>} />
```

### Step 8: Tests

**Unit tests** (requirement_impact_analyzer.py):
1. Requirement addition detection
2. Requirement removal detection
3. Skill promotion (preferred → mandatory)
4. Skill demotion (mandatory → preferred)
5. Experience modification
6. Education modification
7. Candidate satisfaction calculation (skill)
8. Candidate satisfaction calculation (experience)
9. Candidate satisfaction calculation (education)
10. Affected candidates identification
11. Newly qualified candidates
12. Newly disqualified candidates
13. Score impact attribution
14. Multiple requirement changes
15. Zero candidates affected
16. Zero requirements changed
17. Deterministic output
18. Edge case: missing dimension data

**Integration tests** (API endpoints):
1. Full requirement impact lifecycle
2. Pagination
3. Filtering by requirement
4. Filtering by impact type
5. Candidate detail endpoint
6. RBAC enforcement
7. Organization isolation
8. Invalid simulation ID
9. Incomplete simulation (no execution)
10. Failed execution
11. Audit logging

**Critical regression test:**
- Capture JobDescription, CandidateRanking, Candidate, Resume before
- Run requirement simulation
- Assert all are unchanged after

---

## Requirement Change Types

| Change Type | Description | Example |
|-------------|-------------|---------|
| `added` | New requirement in simulation | Add PostgreSQL as mandatory |
| `removed` | Requirement in baseline not in simulation | Remove Redis from preferred |
| `promoted` | Preferred → Mandatory | Docker: preferred → mandatory |
| `demoted` | Mandatory → Preferred | PostgreSQL: mandatory → preferred |
| `modified` | Requirement value changed | Experience: 2+ → 4+ years |

---

## Satisfaction Status Enum

| Status | Meaning |
|--------|---------|
| `SATISFIED` | Candidate meets the requirement |
| `MISSING` | Candidate does not meet the requirement |
| `NOT_APPLICABLE` | Requirement not present in this config |

---

## Impact Categories

| Category | Threshold | Description |
|----------|-----------|-------------|
| `NO_CANDIDATE_IMPACT` | 0 affected | No candidate satisfaction changed |
| `LOW_CANDIDATE_IMPACT` | 1-5 affected | Few candidates impacted |
| `MODERATE_CANDIDATE_IMPACT` | 6-20 affected | Moderate number impacted |
| `HIGH_CANDIDATE_IMPACT` | 21+ affected | Many candidates impacted |

---

## Edge Cases

1. **No completed execution**: Return error message, no analysis
2. **No requirement changes**: Return empty change list, zero impact
3. **No candidates in pool**: Return analysis with zero candidate metrics
4. **All candidates affected**: Handle gracefully
5. **Multiple execution IDs**: Use latest completed by default
6. **Missing dimension data**: Default to 0 for score attribution
7. **Duplicate skills in change detection**: Use `normalize_skill()` (already exists)

---

## Performance Considerations

- Analysis is computed on-demand (not persisted) since it derives from existing data
- For 1000 candidates × 10 requirements: ~10,000 satisfaction checks (fast, no DB calls)
- Skill satisfaction uses `MatchingEngine.skill_matches()` which is pure CPU
- Pagination prevents loading all candidates into memory
- No N+1 queries (loads results in bulk via `list_by_execution()`)

---

## Security

- All endpoints require authentication
- RBAC: admin, hr, recruiter roles only
- Organization isolation via scenario ownership
- Audit logging for all access
- No raw resume text exposed
- No sensitive personal data in requirement analysis

---

## Definition of Done Checklist

- [ ] RequirementImpactAnalyzer service created
- [ ] Requirement impact schemas created
- [ ] API endpoints created (4 endpoints)
- [ ] Frontend types created
- [ ] Frontend API methods added
- [ ] Requirement Impact page created
- [ ] Requirement impact table component created
- [ ] Candidate requirement detail component created
- [ ] Navigation updated in SimulationDetails
- [ ] Route added in App.tsx
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Critical regression test passes (no live data modified)
- [ ] No fake data used
- [ ] Existing Phase 3/4 logic reused
- [ ] Documentation updated
