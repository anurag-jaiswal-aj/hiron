# Phase 17 Implementation Gate: Testing & QA

## 1. Objective
Comprehensive testing pass across all features. Fill gaps in test coverage, run E2E tests, verify accessibility, and achieve AI benchmarking compliance.

## 2. Exact Roadmap Requirements
**Backend Tasks**:
- Achieve ≥ 80% unit test coverage
- Complete integration test suite for all 60 endpoints
- Run full API contract compliance tests

**Frontend Tasks**:
- Component tests for all critical components (score card, Kanban, forms)
- Accessibility audit with axe-core on all 17 screens
- Cross-browser testing (Chrome, Firefox, Safari, Edge)
- Responsive testing at all breakpoints

**AI Tasks**:
- Run scoring benchmark on 100-candidate evaluation dataset
- Verify score distribution is reasonable (not all 90+ or all < 50)
- Verify confidence scores correlate with data completeness

**Testing Tasks**:
- E2E: complete user journey (login → create job → upload resume → parse → score → move stage → hire)
- E2E: multi-tenant isolation journey (Tenant A and B cannot see each other's data)
- E2E: role-based journeys (org_admin, recruiter, hiring_manager see appropriate UI)
- Accessibility: WCAG 2.2 AA compliance audit on all screens
- Performance: re-run all benchmarks from Phase 15

## 3. Existing Implementation
- **Backend Tests**: 92 files exist in `apps/api/tests/`. Test infrastructure using `pytest`, `pytest-asyncio`, and `pytest-cov` is present.
- **Frontend E2E**: 24 specs exist in `apps/web/e2e/` utilizing Playwright.
- **AI Tests**: A rudimentary AI scoring test exists (`test_ai_scoring_benchmark.py`) but only evaluates a single mock candidate.
- **CI Workflows**: GitHub Actions configuration exists (`test.yml`, `ci.yml`) but strictly runs only backend Python tests.

## 4. Existing Tests (Pre-completed Requirements)
- **E2E Complete User Journey**: Implemented in backend (`test_e2e_full_recruitment_workflow.py`) and partially in frontend Playwright specs.
- **E2E Multi-tenant Isolation**: Implemented in backend (`test_e2e_multi_tenant_isolation.py`).
- **E2E Role-based Journeys**: Implemented in backend (`test_e2e_rbac_user_journeys.py`) and frontend (`rbac.spec.ts`).

## 5. Missing Requirements
- **Frontend Component Tests**: Absolutely zero unit/component tests (e.g., Vitest + React Testing Library) exist for critical UI components.
- **Accessibility Audit**: `axe-core` is entirely absent from the frontend toolchain. No WCAG 2.2 AA automated audits are configured or executed.
- **Cross-Browser & Responsive E2E**: `playwright.config.ts` currently restricts execution strictly to `chromium` and lacks configurations for Firefox, Safari, Edge, or mobile/tablet breakpoints.
- **AI 100-Candidate Benchmark**: Missing. Only 1 mock candidate is evaluated.
- **CI Test Execution**: Frontend testing, component testing, E2E browser testing, and coverage gating are absent from GitHub Actions CI.
- **Coverage Validation**: Needs an aggregated `pytest-cov` execution to prove ≥ 80% coverage on the 60 API endpoints.

## 6. Proposed Implementation Scope
- **Backend**: Configure `pytest-cov` to enforce an 80% minimum coverage threshold. Validate integration tests cover all 60 endpoints.
- **Frontend (Component Testing)**: Install Vitest and React Testing Library. Implement component tests targeting the score card, Kanban board, and critical forms.
- **Frontend (E2E & Accessibility)**: Install `@axe-core/playwright`. Expand `playwright.config.ts` to include WebKit, Firefox, Edge, and viewport-specific mobile/tablet projects. Implement WCAG 2.2 AA audit assertions on all 17 screens.
- **AI**: Implement the required 100-candidate dataset fixture and update `test_ai_scoring_benchmark.py` to evaluate distribution and correlation heuristics.
- **CI/CD**: Update `.github/workflows/test.yml` and `ci.yml` to execute Playwright, Vitest, and Axe-core, ensuring no regressions.
- **Performance**: Execute and formally record Phase 15 benchmarks into a final Phase 17 report artifact.

## 7. Exact Files Expected to Change
- `apps/api/pyproject.toml` (cov thresholding)
- `apps/api/tests/test_ai_scoring_benchmark.py` (Dataset expansion)
- `apps/api/tests/fixtures/candidates_100.json` (New data fixture)
- `apps/web/package.json` (Vitest, RTL, Axe-core dependencies)
- `apps/web/playwright.config.ts` (Browsers & Viewports)
- `apps/web/e2e/accessibility.spec.ts` (New Axe-core tests)
- `apps/web/vitest.config.ts` (New)
- `apps/web/components/**/*.test.tsx` (New component tests)
- `.github/workflows/test.yml` (Adding frontend/Playwright steps)
- `docs/Phase_17_QA_Report.md` (New deliverable report)

## 8. Test Strategy
All new additions in this phase are intrinsically tests. We will systematically configure the CI pipeline to execute them. If the CI passes, the Phase 17 test strategy naturally passes.

## 9. Acceptance Criteria
- [ ] Backend unit test coverage ≥ 80% verified by `pytest-cov`
- [ ] All 60 API endpoints have integration tests
- [ ] E2E tests pass for all user journeys
- [ ] WCAG 2.2 AA audit passes (zero critical, zero high) via Axe-core
- [ ] Cross-browser testing passes on Chrome, Firefox, Safari, Edge
- [ ] Responsive testing passes at mobile, tablet, desktop breakpoints
- [ ] AI benchmark scores within expected distribution on 100-candidate dataset

## 10. Risks/Blockers
- **Playwright System Dependencies**: Running full cross-browser E2E inside the current agent/IDE container environment may lack WebKit/Firefox binaries or GTK dependencies.

## 11. Dependencies
- Relies heavily on previous AI pipelines (Phase 13), E2E integrations (Phase 16), and infrastructure setups.

## 12. Explicit Non-Goals
- Do NOT rewrite existing Phase 16 multi-tenant or RBAC tests unless they break under cross-browser configs.
- Do NOT introduce new application features. This is strictly a testing/QA phase.

## 13. Commit Boundary
- The Phase 17 work will be captured in a unified commit: `test: implement comprehensive QA, component testing, and accessibility`.

## 14. Final Readiness Verdict
**READY FOR IMPLEMENTATION**
