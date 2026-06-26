## Burst Plan
**Goal:** Make the Claude setup "guide" modal (opened from the sidebar) center on the viewport instead of being clamped to the left sidebar pane.
**CHARTER alignment:** Supports "Frontend connected to live backend" objective and overall UX quality of the Claude-connection onboarding flow (no specific Hard Spec; UX defect fix).
**Streams:** single

### Stream A - portal-the-modal
- Scope (files WRITTEN):
  - `frontend/components/layout/ClaudeSetupModal.tsx`
- Excluded:
  - `frontend/components/layout/Sidebar.tsx` (no change needed — call site stays)
  - `frontend/app/(dashboard)/layout.tsx` (no change needed — transform wrapper is intentional for mobile off-canvas slide)
- Exports: `ClaudeSetupModal` component — same props (`userName`, `onDone`, `onSkip`), same behaviour, now rendered via React portal into `document.body`.
- Dependency: none (uses `react-dom`'s `createPortal`, already a transitive dependency of Next.js/React; no new package).
- Builder: claude

**Root cause:** The sidebar wrapper at `layout.tsx:88-93` applies `transition-transform` + `translate-x-*`. A `transform` on an ancestor establishes a containing block, so `position: fixed` descendants resolve against the 256px-wide sidebar box instead of the viewport. `ClaudeSetupModal` is rendered from inside `Sidebar.tsx:106`, making it a descendant of that transformed wrapper — hence the modal is clamped to the left pane. The auto-onboarding instance rendered at `layout.tsx:107` is outside the transform and already centers correctly, confirming the diagnosis.

**Fix:** Render the modal through `createPortal(..., document.body)` so it escapes the transformed sidebar ancestor and `fixed inset-0 flex items-center justify-center` centers on the viewport. Add a `mounted` guard (`useState(false)` + `useEffect`) so the portal is only created client-side (SSR/hydration safety in the Next.js App Router). Returns `null` until mounted. No markup/styling changes to the modal body itself.

**Shared files:** none
**Integration gate:**
- TypeScript compiles (`npx tsc --noEmit` or `npm run build` in `frontend/`).
- Manual UI: click the "guide" affordance in the sidebar (state where `user.mcp_setup_done` is true) — modal renders centered on the viewport, backdrop covers full screen, Skip/✕/Next/Back/Done all still work.
- Regression: auto-onboarding instance (`!mcp_setup_done`) still appears and remains centered.
**Deferred to next Burst:** none
