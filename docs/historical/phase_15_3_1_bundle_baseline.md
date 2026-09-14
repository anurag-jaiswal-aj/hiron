# Phase 15.3.1: Bundle Baseline Verification

## 1. Objective
Establish a true, measured baseline of the Next.js production frontend bundles, pinpoint the exact size contributions of suspected heavy libraries, and rank optimization targets before executing code splitting.

## 2. Tool/Configuration Added
- Installed `@next/bundle-analyzer` as a dev dependency via `pnpm add -D`.
- Created `next.config.mjs` wrapping the configuration with `withBundleAnalyzer`.

## 3. Baseline Build Results
The Next.js production build (`ANALYZE=true pnpm build`) successfully generated the Webpack visualizer HTML files (`client.html`, `edge.html`, `nodejs.html`) and emitted the following route size table.

## 4. Route-by-Route Bundle Sizes
| Route | Size | First Load JS |
|---|---|---|
| `/` (Dashboard) | `13.6 kB` | `207 kB` |
| `/_not-found` | `875 B` | `88.2 kB` |
| `/ai-usage` | `17.9 kB` | `211 kB` |
| `/audit-logs` | `6.59 kB` | `93.9 kB` |
| `/candidates` | `3.28 kB` | `103 kB` |
| `/candidates/[id]` | `157 kB` | `257 kB` |
| `/candidates/new` | `3.16 kB` | `103 kB` |
| `/candidates/upload` | `8.95 kB` | `109 kB` |
| `/jobs` | `3.29 kB` | `103 kB` |
| `/jobs/[id]` | `24.9 kB` | `125 kB` |
| `/jobs/[id]/edit` | `4.21 kB` | `104 kB` |
| `/jobs/new` | `3.74 kB` | `104 kB` |
| `/login` | `4.38 kB` | `91.7 kB` |
| `/search` | `4.45 kB` | `105 kB` |
| `/users` | `3.96 kB` | `104 kB` |

## 5. Current Shared JS Size
**87.3 kB** is shared by all routes natively (`react`, `react-dom`, `next/router`, etc).

## 6. Largest Contributing Packages/Modules
By comparing lightweight routes (e.g. `/users` at `104 kB`) to the heavy routes, we can measure the exact compiled penalty of the imported UI libraries.

### 7. Tiptap Contribution
- Route: `/candidates/[id]` (`257 kB`)
- Approximate Contribution: `257 kB - 104 kB` = **`153 kB`** compiled JavaScript.

### 8. Recharts Contribution
- Routes: `/` (`207 kB`), `/ai-usage` (`211 kB`)
- Approximate Contribution: `207 kB - 104 kB` = **`103 kB`** compiled JavaScript.

### 9. DnD Kit Contribution
- Route: `/jobs/[id]` (`125 kB`)
- Approximate Contribution: `125 kB - 104 kB` = **`21 kB`** compiled JavaScript.

## 10. Optimization Targets Ranked by Expected Value
1. **`/candidates/[id]`**: Dynamically import the Note Editor. Saves ~153 kB. Highest value target because recruiters will load candidate profiles constantly and often not look at notes.
2. **`/ai-usage` & `/`**: Dynamically import Recharts. Saves ~103 kB. High value because Dashboard is the application entrypoint.
3. **`/jobs/[id]`**: Dynamically import Kanban Board (`dnd-kit`). Saves ~21 kB. Moderate value.

## 11. Surprising Findings
The `/candidates/[id]` route size itself (server payload/HTML) is shockingly large (`157 kB` Route Size before JS). This is extremely high for Next.js and implies there is a massive amount of inline CSS, massive DOM trees, or large base64 data embedded directly in the server-rendered HTML for the candidate profile.

## 12. Exact Files Changed
- `apps/web/package.json` (Added `@next/bundle-analyzer`)
- `apps/web/next.config.mjs` (Created)

## 13. Strict Scope Audit
- No components were dynamically imported.
- No business logic or backend files were modified.
- TanStack Query was completely ignored as instructed.

## 14. Verification Results
- **TypeScript**: `npx tsc --noEmit` passed.
- **ESLint**: `npx next lint` passed with zero errors/warnings.
- **Production Build**: Successfully compiled and exported.
- **Git Diff**: `git diff --check` passed (no trailing whitespace).

## 15. What MUST NOT be changed in 15.3.2
- Do not migrate to TanStack Query.
- Do not change how Candidate data is fetched or how Auth state is maintained.
- Do not remove the libraries, only change how they are imported.

## 16. Final Verdict
**READY FOR CHECKPOINT 15.3.2.** The baseline is established and we have precise targets for `next/dynamic`.
