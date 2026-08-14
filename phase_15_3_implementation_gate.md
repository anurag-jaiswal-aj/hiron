# Phase 15.3: Frontend Optimization Implementation Gate

## 1. Objective
Perform an audit of the frontend architecture, identify rendering and bundle size bottlenecks, and propose exact optimizations to meet the Phase 15 performance requirements without introducing unnecessary architectural churn.

## 2. Exact Phase 15.3 Requirements from Roadmap
- Implement code splitting per route (Next.js dynamic imports)
- Optimize bundle size (analyze with `@next/bundle-analyzer`)
- Implement image optimization (if applicable)
- Add `staleTime` and `gcTime` to TanStack Query configurations
- Verify Lighthouse scores (target: 90+ performance)

## 3. Current Frontend Architecture
- Framework: Next.js 14 App Router.
- Data Fetching: Vanilla React `useEffect` state combined with a custom `apiFetch` wrapper (`apps/web/lib/api.ts`), along with Next.js Server Components.
- Styling: Custom CSS (`apps/web/app/globals.css`).

## 4. Current Bundle Analysis
Executed `npm run build` to evaluate current production chunks:
- **Shared First Load JS**: `87.3 kB`
- **`/candidates/[id]`**: `257 kB` (Largest route)
- **`/ai-usage`**: `211 kB`
- **`/` (Dashboard)**: `207 kB`
- **`/jobs/[id]`**: `125 kB`

*Note: `@next/bundle-analyzer` is currently not installed in `package.json`.*

## 5. Current TanStack Query Configuration
**Not Applicable (or Scope Creep).** 
`@tanstack/react-query` is entirely absent from the `package.json` and the codebase. The application currently manages data fetching via native `fetch` and `useEffect`. To satisfy this roadmap bullet point exactly, we would have to migrate the entire frontend data fetching layer to TanStack Query, which violates the "No new features / Performance improvements only" rule. **Recommendation: Skip TanStack Query migration.**

## 6. Current Image Usage
**Not Applicable.**
A grep of the application code reveals zero instances of `next/image` or native HTML `<img` tags. The application is completely text and UI-driven.

## 7. Lighthouse Baseline
To be formally established via Playwright/Lighthouse integration during Phase 15.4 (Load Testing). However, the primary penalty to Lighthouse Performance (TTI / LCP) currently stems from the monolithic initial JS bundles identified in Step 4.

## 8. Identified Bottlenecks
1. **`@tiptap` Ecosystem**: Statically imported in `CandidateNotesTab.tsx`. It forces all users visiting a candidate profile to download the heavy rich-text editor bundle (~100kB+), even if they never interact with the Notes tab.
2. **`recharts`**: Statically imported in `ScoreDistributionChart.tsx` and `UsageTrendChart.tsx`, heavily penalizing the initial load of the Dashboard and AI Usage pages.
3. **`@dnd-kit`**: Statically imported in `PipelineKanbanBoard.tsx`, inflating the Job pipeline view.

## 9. Existing Optimizations Already Present
- Core routing relies on Next.js Server Components, shipping minimal JS for purely structural layouts.
- Reusable `apiFetch` properly centralizes request deduplication logic for auth token refreshing.

## 10. Proposed Optimizations
1. **Install `@next/bundle-analyzer`**: Configure it within a new `next.config.mjs` for visual verification of chunk separation.
2. **Dynamic Imports (`next/dynamic`)**:
   - Dynamically import `NoteEditor` and `CandidateNotesTab` inside `/candidates/[id]`.
   - Dynamically import `ScoreDistributionChart` inside the Dashboard.
   - Dynamically import `UsageTrendChart` inside `/ai-usage`.
   - Dynamically import `PipelineKanbanBoard` inside `/jobs/[id]`.

## 11. Expected Impact
- **`/candidates/[id]`**: JS bundle reduction from `257 kB` down to `~130 kB`.
- **`/ai-usage` & `/`**: JS bundle reduction from `~210 kB` down to `~110 kB`.
- **TTI**: Faster Time-to-Interactive on key candidate and dashboard routes.

## 12. Risks
- **Cumulative Layout Shift (CLS)**: Dynamic imports asynchronously load components. If loading skeletons are not sized to match the final components, CLS will negatively impact the Lighthouse score. *Mitigation: Provide strict height placeholders in the `next/dynamic` loading fallback.*

## 13. Exact Files Expected to Change
- `apps/web/package.json`
- `apps/web/next.config.mjs` (New)
- `apps/web/components/notes/CandidateNotesTab.tsx`
- `apps/web/app/candidates/[id]/page.tsx`
- `apps/web/components/dashboard/ScoreDistributionChart.tsx`
- `apps/web/app/page.tsx`
- `apps/web/components/ai-usage/UsageTrendChart.tsx`
- `apps/web/app/ai-usage/page.tsx`
- `apps/web/components/pipeline/PipelineKanbanBoard.tsx`
- `apps/web/app/jobs/[id]/page.tsx`

## 14. Strict Scope Boundaries
- **No Data Fetching Refactors**: We will not migrate to TanStack Query.
- **No Backend Modifications**: Strictly frontend bundle sizing.
- **No UI Changes**: Visual appearance must remain identical (excluding loading skeletons).

## 15. Proposed Implementation Checkpoints
- **15.3.1**: Bundle Analyzer Setup & Baseline Visualization
- **15.3.2**: Dynamic Component Extraction (Tiptap, Recharts, Dnd-kit)
- **15.3.3**: Final Build Verification & E2E Validation

## 16. Testing/Verification Strategy
- Execute `npm run build` to quantitatively verify bundle size reductions in the CLI output.
- Execute `npm run test:e2e` to ensure dynamic component loaders do not break Playwright assertions (which should natively wait for DOM elements to appear).

## 17. Final Verdict
**READY TO PROCEED** (Pending user confirmation regarding the TanStack Query roadmap omission).
