---
phase: 20-cold-start-call-flow-repair
plan: 01
subsystem: calls
tags: [cold-start, callkit, voip, webrtc, coordinator, react-native]

# Dependency graph
requires: []
provides:
  - "ColdStartCoordinator singleton module owning all cold start call state"
  - "Simplified App.tsx cold start useEffect (~34 lines, down from ~200)"
  - "Cleaned CallKitService without duplicate cold start state"
  - "CallScreen reading from ColdStartCoordinator instead of global state"
affects: [20-02-PLAN, 20-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Singleton coordinator pattern for cross-module state consolidation", "Backward-compat global proxy with getter delegation"]

key-files:
  created:
    - "src/services/ColdStartCoordinator.ts"
  modified:
    - "index.js"
    - "App.tsx"
    - "src/services/CallKitService.ts"
    - "src/screens/CallScreen.tsx"
    - "src/services/MessagingService.ts"

key-decisions:
  - "ColdStartCoordinator uses lazy require() for dependencies to avoid circular imports at module load time"
  - "Kept global.__coldStartCall as read-only proxy with getters for backward compatibility during transition"
  - "Two navigate('Call') calls in ColdStartCoordinator are mutually exclusive per cold start call (PATH A/B vs PATH C answer)"

patterns-established:
  - "ColdStartCoordinator singleton: all cold start state reads/writes go through one module"
  - "Backward-compat proxy pattern: global.__coldStartCall delegates to ColdStartCoordinator getters"

requirements-completed: [COLD-01, COLD-03]

# Metrics
duration: 8min
completed: 2026-03-30
---

# Phase 20 Plan 01: Cold Start Coordinator Extraction Summary

**Extracted cold start call coordination into ColdStartCoordinator singleton, reducing App.tsx cold start logic from ~200 lines to ~34 lines and eliminating duplicate state across 4 files**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-30T05:38:18Z
- **Completed:** 2026-03-30T05:46:41Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments
- Created ColdStartCoordinator.ts (310 lines) as single source of truth for all cold start call state (answerUUID, declineUUID, audioSessionActivated, callData, callEndedDuringBoot)
- Removed ~370 lines of duplicated cold start logic from App.tsx, CallKitService.ts, and global state
- Eliminated race condition vectors by consolidating state tracking into one module with a `handled` guard
- Maintained backward compatibility via global.__coldStartCall proxy object with getter delegation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ColdStartCoordinator module and update index.js** - `a61d2b1` (feat)
2. **Task 2: Refactor App.tsx to delegate to ColdStartCoordinator** - `a7ee2a8` (refactor)

## Files Created/Modified
- `src/services/ColdStartCoordinator.ts` - New singleton module owning all cold start call state and 3-path SDP retrieval
- `index.js` - Updated to write to ColdStartCoordinator instead of global.__coldStartCall directly
- `App.tsx` - Removed coldStartHandledRef, cold-start-answer useEffect, simplified coordinator useEffect from ~200 to ~34 lines
- `src/services/CallKitService.ts` - Removed coldStartAnswerUUID/coldStartDeclineUUID fields and 5 related methods, now delegates to ColdStartCoordinator
- `src/screens/CallScreen.tsx` - Reads from ColdStartCoordinator instead of global.__coldStartCall
- `src/services/MessagingService.ts` - Writes callEndedDuringBoot to ColdStartCoordinator instead of global

## Decisions Made
- Used lazy `require()` inside ColdStartCoordinator methods to avoid circular imports (ColdStartCoordinator -> CallKitService -> ColdStartCoordinator)
- Kept `global.__coldStartCall` as a read-only proxy object with getters delegating to ColdStartCoordinator -- ensures any code not yet migrated still works
- Two `navigate('Call')` calls exist in ColdStartCoordinator but are mutually exclusive per cold start call (one for PATH A/B success, one for incoming-call handler PATH C)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Updated MessagingService.ts __callEndedDuringBoot reference**
- **Found during:** Task 2 (Refactor App.tsx)
- **Issue:** MessagingService.ts line 252-253 wrote directly to `global.__callEndedDuringBoot` -- this would bypass ColdStartCoordinator and create a state inconsistency
- **Fix:** Replaced with `ColdStartCoordinator.setCallEndedDuringBoot(message.from)` using lazy require
- **Files modified:** src/services/MessagingService.ts
- **Verification:** TypeScript compiles clean, grep confirms no remaining global.__callEndedDuringBoot writes
- **Committed in:** a7ee2a8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential fix to prevent state inconsistency. MessagingService was not listed in the plan's files but wrote to the global that ColdStartCoordinator now owns.

## Issues Encountered
- TypeScript `--noEmit` shows pre-existing errors from node_modules (react-navigation type conflicts, i18n JSON imports, RNFS default export) -- these are unrelated to our changes and existed before. Our code compiles clean with `--skipLibCheck`.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is wired with real data sources.

## Next Phase Readiness
- ColdStartCoordinator is ready for Plan 02 (SDP retrieval hardening) and Plan 03 (call-ended race fix)
- All cold start state is now accessible via one import: `import ColdStartCoordinator from './services/ColdStartCoordinator'`

---
*Phase: 20-cold-start-call-flow-repair*
*Completed: 2026-03-30*
