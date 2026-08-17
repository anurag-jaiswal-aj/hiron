# Phase 10 Pipeline / Kanban Readiness Audit

## 1. Objective
Perform a non-destructive readiness audit of the Phase 10 (Pipeline / Kanban) implementation against the requirements documented in `IMPLEMENTATION_ROADMAP.md`. Determine the exact status of the feature, identify gaps, and recommend the correct path forward before formally beginning the phase execution.

## 2. Roadmap Requirements
Phase 10 requires the implementation of a drag-and-drop Kanban board for managing candidate stages within a job.
Key features include:
- Draggable candidate cards across stage columns
- Atomic movement of candidates between stages with transition history
- Candidate shortlisting (for HM review) and rejection (with reason)
- Cross-job and same-stage protection logic
- Mobile-friendly stage selector
- Role-based authorization constraints

## 3. Existing Implementation Inventory

| Requirement | Expected | Actual Implementation | Status | Evidence |
| --- | --- | --- | --- | --- |
| Kanban Board & Drag-Drop | `@dnd-kit` implementation | Implemented via `PipelineKanbanBoard.tsx` | IMPLEMENTED | `apps/web/components/pipeline/PipelineKanbanBoard.tsx` |
| Move candidate endpoint | `POST /pipeline/move` | Working FastAPI endpoint backing onto `PipelineService` | IMPLEMENTED | `apps/api/hiron/pipeline/router.py:move_candidate_stage_endpoint` |
| Stage History endpoint | `GET /jobs/{}/candidates/{}/stage-history` | Fully implemented API handling timeline reads | IMPLEMENTED | `apps/api/hiron/pipeline/router.py:get_stage_history_endpoint` |
| Shortlist Candidate endpoint | `POST /jobs/{}/candidates/{}/shortlist` | Updates `is_shortlisted` on `job_candidates` | IMPLEMENTED | `apps/api/hiron/pipeline/router.py:shortlist_candidate_endpoint` |
| Reject Candidate endpoint | `POST /jobs/{}/candidates/{}/reject` | Transitions to rejected stage and logs reason in history | IMPLEMENTED | `apps/api/hiron/pipeline/router.py:reject_candidate_endpoint` |
| Create history on move | `candidate_stage_history` table insert | Integrated safely in `PipelineService.move_candidate_stage` | IMPLEMENTED | `apps/api/hiron/pipeline/service.py:move_candidate_stage` |
| Atomic update stage ID | Update `job_candidates.current_stage_id` | Database ORM updates managed synchronously with history inserts | IMPLEMENTED | `apps/api/hiron/pipeline/repository.py:update_job_candidate_stage` |
| Candidate card UI | Displays name, title, score, confidence | Present in `KanbanCandidateCard.tsx` | IMPLEMENTED | `apps/web/components/pipeline/KanbanCandidateCard.tsx` |
| Rejection Modal | Modal with reason | Included inside `CandidateActionModal.tsx` | IMPLEMENTED | `apps/web/components/pipeline/CandidateActionModal.tsx` |
| Mobile stage selector | Mobile dropdown selector | `select` overlay triggering on `< 768px` | IMPLEMENTED | `apps/web/components/pipeline/PipelineKanbanBoard.tsx` |

## 4. Backend Architecture
The backend is structured conventionally per the architectural guidelines:
- **Router**: `apps/api/hiron/pipeline/router.py` exposes 5 REST endpoints (Move, History, Shortlist, Reject, Board view).
- **Service**: `apps/api/hiron/pipeline/service.py` houses strict business validation (e.g. `_validate_move_permissions`, checking job congruence).
- **Repository**: `apps/api/hiron/pipeline/repository.py` handles direct ORM operations (fetching stages, updating associations, inserting history logs).
- **Models**: Built cleanly mapping to PostgreSQL (`candidate_stage_history`).
- **Schemas**: Validated with Pydantic (`MoveCandidateStageRequest`, etc.).
- **Transaction Boundaries**: Bound correctly to FastAPI's dependency injection (`get_db`) which commits on a 200 OK route return, guaranteeing atomicity for the `update_job_candidate_stage` + `create_stage_history` paired operation.

## 5. Stage Transition Model
- **Pipeline Stages**: Standardized list fetched dynamically.
- **Job Ownership**: `PipelineService` explicitly blocks moves if `target_stage.job_id != job_candidate.job_id` (422 PipelineStageValidationError).
- **Same-stage Protection**: Blocked with 422 if `job_candidate.current_stage_id == to_stage_id`.
- **Rejected Handling**: Handled seamlessly by `reject_candidate`, auto-detecting terminal stages like "rejected" or "disqualified".

## 6. Stage History
- **Actor/Timestamp**: Accurately mapped to `current_user.id` and UTC `now`.
- **Flow**: Source `from_stage` to target `to_stage` recorded securely.
- **Persistence**: Hooked automatically to any `move_candidate_stage` or `reject_candidate` call.

## 7. Shortlist / Reject
- **Shortlist**: Toggles `is_shortlisted = True` in `job_candidates`. (Database schema supports this).
- **Reject**: Wraps the standard transition mechanics but automatically determines the rejection stage and applies `note=f"Rejected: {reason}"` to the history log.

## 8. RBAC & Tenant Isolation
- **Permissions**: `PipelineService._validate_move_permissions` ensures `role in ["org_admin", "recruiter"]`. Hiring Managers (HMs) explicitly trigger a `403 Forbidden` if attempting transitions.
- **Tenant Isolation**: Applied uniformly across the repository data-access layer (`tenant_id=tenant_id`). No cross-tenant reads or writes are possible.

## 9. Frontend Readiness
- **Pipeline Route**: Sub-page of Job Detail loaded conditionally on the `Kanban` tab.
- **Drag-and-Drop**: Leverages `@dnd-kit/core` seamlessly.
- **Candidate Cards**: Rich cards with Fit Score and Confidence metric badges.
- **Optimistic Updates**: `handleDragEnd` in `PipelineKanbanBoard` synchronously mutates the React array state immediately and reverts gracefully inside the `catch` block if the API fails.
- **Mobile Behavior**: Evaluates `window.innerWidth` and switches dynamically to a single-column dropdown UI structure.
- **Conclusion**: The frontend is fully IMPLEMENTED.

## 10. Existing Test Coverage
- **`apps/api/tests/test_pipeline_api.py`**: Validates route bindings. (Heavily relies on `AsyncMock` — NOT true E2E).
- **`apps/api/tests/test_pipeline_service.py`**: Focuses on business rules (e.g. `test_hiring_manager_move_candidate_raises_403`, `test_move_candidate_same_stage_raises_validation_error`).
- **`apps/api/tests/test_pipeline_repository.py`**: Confirms basic ORM execution.
- **`apps/web/e2e/pipeline.spec.ts`**: Playwright test simulating drag-and-drop and verifying layout, BUT it relies on mocking the backend API via `page.route`.

## 11. Gaps / Blockers
- **Missing Implementation**: None. The feature code is completely written.
- **Missing Tests**: True integration/E2E tests (unmocked) validating the real-world pipeline data manipulation across database boundaries are missing.
- **Missing Production Validation**: The pipeline module has not been tested via E2E production data flow.
- **Blockers**: No blockers exist preventing validation.

## 12. Recommended Implementation / Validation Sequence
Because the codebase is already entirely populated from a previous commit `feat(pipeline): implement Phase 10 pipeline kanban`, implementation is complete. We must execute **Validation**.

1. **Verify Unmocked Flow**: Write or execute an integration script to transition a real candidate on the local testing DB to verify `job_candidates` updates alongside `candidate_stage_history`.
2. **Production Validation**: Execute a single E2E pipeline transition trace on the production workspace to confirm tenant isolation, Kanban API stability, and correct score propagation.

## 13. Acceptance Criteria Matrix

| Criterion | Evidence | Status |
| --- | --- | --- |
| Kanban board shows stages with cards | `PipelineKanbanBoard.tsx` maps stages | PARTIAL (Needs validation) |
| Drag-and-drop moves candidate | `@dnd-kit` tied to `POST /pipeline/move` | PARTIAL (Needs validation) |
| Move creates stage history | `CandidateStageHistory` insert active | PARTIAL (Needs validation) |
| Shortlist toggles `isShortlisted` | `shortlist_job_candidate` ORM logic | PARTIAL (Needs validation) |
| Reject moves to rejected stage | `reject_candidate` logic | PARTIAL (Needs validation) |
| HM can view but not move | `_validate_move_permissions` | PARTIAL (Needs validation) |
| Mobile stage selector | `<select>` hook active under 768px | PARTIAL (Needs validation) |
| Cards show Phase 8 score/confidence | `KanbanCandidateCard.tsx` badges present | PARTIAL (Needs validation) |

*Status is marked PARTIAL because while the code perfectly implements the criteria, it lacks definitive unmocked validation.*

## 14. Final Readiness Decision

**PHASE 10: READY FOR VALIDATION**

*Reasoning*: Every single technical requirement defined in the `IMPLEMENTATION_ROADMAP.md` for Phase 10 has already been fully programmed in both the frontend (React/DND-kit) and the backend (FastAPI/SQLAlchemy). Therefore, we do not need to implement new features. We must proceed immediately to a comprehensive E2E validation cycle to prove the implementation behaves correctly against real databases.
