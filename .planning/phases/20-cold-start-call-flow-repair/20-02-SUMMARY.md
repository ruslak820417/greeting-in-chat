---
phase: 20-cold-start-call-flow-repair
plan: 02
subsystem: calls
tags: [cold-start, callkit, audio-session, webrtc, incallmanager, react-native]

# Dependency graph
requires:
  - phase: 20-01
    provides: "ColdStartCoordinator singleton module owning all cold start call state"
provides:
  - "Correct audio session lifecycle for cold start incoming calls (InCallManager.stop() skipped)"
  - "RTCAudioSession re-notification after peer connection creation on cold start"
  - "Cold start audio state cleanup after use (prevents stale state on subsequent calls)"
  - "Validated end-to-end audio handoff: CallKit -> index.js -> ColdStartCoordinator -> CallScreen"
affects: [20-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Cold start audio guard: skip InCallManager.stop() when CallKit already activated audio session", "Post-answerCall RTCAudioSession re-notification pattern for WebRTC audio binding"]

key-files:
  created: []
  modified:
    - "src/screens/CallScreen.tsx"
    - "index.js"

key-decisions:
  - "Use ColdStartCoordinator.hasAnswer (boolean) instead of .answerUUID (nullable string) for isColdStartIncoming check -- cleaner semantics"
  - "Clear cold start audio state after re-notification so subsequent warm calls perform normal InCallManager.stop() reset"
  - "RTCAudioBridge native module confirmed correct -- no changes needed (activateAudioSession already implements GetStream/LiveKit pattern)"
  - "AppDelegate.swift confirmed correct -- PendingVoIPCall stored synchronously, reportNewIncomingCall called synchronously"

patterns-established:
  - "Cold start audio guard: ColdStartCoordinator.hasAnswer gates InCallManager.stop() skip"
  - "Audio state cleanup: setAudioSessionActivated(false) after cold start audio re-notification prevents stale state"

requirements-completed: [COLD-02]

# Metrics
duration: 2min
completed: 2026-03-30
---

# Phase 20 Plan 02: Audio Session Lifecycle Fix Summary

**Fixed cold start audio by gating InCallManager.stop() via ColdStartCoordinator.hasAnswer and adding post-answerCall RTCAudioSession re-notification with state cleanup**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-30T05:49:17Z
- **Completed:** 2026-03-30T05:51:36Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- Fixed isColdStartIncoming check to use ColdStartCoordinator.hasAnswer (boolean getter) instead of .answerUUID (nullable string) for cleaner semantics
- Added ColdStartCoordinator.setAudioSessionActivated(false) cleanup after audio re-notification -- prevents subsequent warm calls from incorrectly skipping InCallManager.stop()
- Updated diagnostic logs in both CallScreen.tsx and index.js to use hasAnswer= format consistently
- Validated RTCAudioBridge native module and AppDelegate.swift -- both already correct, no changes needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix CallScreen audio session lifecycle for cold start** - `deb1fbb` (feat)
2. **Task 2: Validate RTCAudioBridge native module and audio session handoff** - `13337bc` (feat)

## Files Created/Modified
- `src/screens/CallScreen.tsx` - Fixed isColdStartIncoming to use .hasAnswer, added audio state cleanup after re-notification, updated log format
- `index.js` - Updated diagnostic log after didLoadWithEvents to use ColdStartCoordinator.hasAnswer format

## Decisions Made
- Used ColdStartCoordinator.hasAnswer (boolean) over .answerUUID (nullable string) for the isColdStartIncoming guard -- boolean semantics are cleaner for conditional checks
- Confirmed RTCAudioBridge.swift and AppDelegate.swift are already correct from prior builds -- no modifications needed
- Added explicit audio state cleanup (setAudioSessionActivated(false)) after cold start re-notification to prevent stale state affecting subsequent calls in the same app session

## Deviations from Plan

None - plan executed exactly as written. The RTCAudioBridge native module and AppDelegate.swift were already in the correct state from prior builds, so Task 2 was primarily validation with a minor index.js diagnostic log update.

## Issues Encountered
- TypeScript `--noEmit` shows pre-existing errors from node_modules (tweetnacl imports, JSX config, JSON module resolution) -- these are unrelated to our changes and existed before Plan 01. Our code compiles clean with `--skipLibCheck`.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is wired with real data sources.

## Next Phase Readiness
- Audio session lifecycle is now correct for cold start incoming calls
- The complete flow is validated: CallKit activates audio -> index.js captures via ColdStartCoordinator -> CallScreen skips InCallManager.stop() -> answerCall creates peer -> RTCAudioSession re-notified -> audio state cleaned up
- Ready for Plan 03 (call-ended race fix) which depends on ColdStartCoordinator

## Self-Check: PASSED

- 20-02-SUMMARY.md: FOUND
- Commit deb1fbb (Task 1): FOUND
- Commit 13337bc (Task 2): FOUND

---
*Phase: 20-cold-start-call-flow-repair*
*Completed: 2026-03-30*
