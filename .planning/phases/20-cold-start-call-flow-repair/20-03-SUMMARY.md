---
phase: 20-cold-start-call-flow-repair
plan: 03
subsystem: calls
tags: [cold-start, voip, turn, sdp, webrtc, dedup, diagnostics]

# Dependency graph
requires:
  - phase: 20-01
    provides: "ColdStartCoordinator singleton module owning all cold start call state"
provides:
  - "TURN servers included in both VoIP push payload and get-call-state response"
  - "getCachedTurnServers() shared function with 1-hour TTL in server/index.js"
  - "Duplicate call offer suppression in MessagingService during cold start"
  - "Structured diagnostic logging with timing for all 3 cold start paths"
  - "getDiagnosticSummary() method for post-call reporting"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["TURN server caching with TTL for reuse across call setup", "Cold start path resolution tracking (A/B/C) with elapsed timing"]

key-files:
  created: []
  modified:
    - "server/index.js"
    - "server/push.js"
    - "src/services/ColdStartCoordinator.ts"
    - "src/services/MessagingService.ts"

key-decisions:
  - "getCachedTurnServers() prefers Metered API dynamic credentials over static env vars, with 1-hour cache TTL"
  - "push.js prefers callData.turnServers (from getCachedTurnServers) over its own static env var lookup for richer TURN coverage"
  - "VoIP payload size check removes SDP (not TURN) when over 4500 bytes -- SDP is larger and can be retrieved via WebSocket"
  - "Duplicate offer suppression uses lazy require to avoid circular imports"

patterns-established:
  - "TURN cache pattern: getCachedTurnServers() with TTL for consistent TURN delivery across push and WebSocket paths"
  - "Cold start path tracking: _resolvedPath, _resolvedSource, _resolvedTurnCount, _resolvedElapsed for diagnostic summary"

requirements-completed: [COLD-03, COLD-04]

# Metrics
duration: 5min
completed: 2026-03-30
---

# Phase 20 Plan 03: SDP Pipeline Hardening and Cold Start Diagnostics Summary

**TURN servers delivered in both VoIP push and get-call-state, duplicate offer suppression for cold start, structured diagnostic logging with timing across all 3 SDP retrieval paths**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-30T05:49:22Z
- **Completed:** 2026-03-30T05:54:36Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments
- Server now includes TURN servers in get-call-state response (cold start PATH B) via getCachedTurnServers() with 1-hour TTL cache
- VoIP push payload includes TURN servers from getCachedTurnServers() (cold start PATH A), with final size validation to stay under Apple's 5KB limit
- MessagingService suppresses duplicate call offers when ColdStartCoordinator has already handled the call via PATH A or PATH B
- ColdStartCoordinator has 30+ structured diagnostic log lines with [ColdStart] prefix, elapsed timing, and FAIL/SUCCESS/TIMEOUT markers for all 3 paths
- getDiagnosticSummary() method returns one-line summary: "COLD_START path=A sdp=voip_push turn=2 elapsed=18ms"
- TURN servers from server call-state response are cached in SignalingClient during PATH B

## Task Commits

Each task was committed atomically:

1. **Task 1: Include TURN servers in server call-state response and VoIP push** - `942efba` (feat)
2. **Task 2: Add duplicate offer suppression and cold start diagnostic logging** - `6dadcd7` (feat)

## Files Created/Modified
- `server/index.js` - Added getCachedTurnServers() with TTL cache, TURN in get-call-state response, TURN in activeCalls entries, async message handler
- `server/push.js` - Prefer callData.turnServers over static env vars in sendVoIPPush, final payload size validation
- `src/services/ColdStartCoordinator.ts` - Structured diagnostic logging for all 3 paths, getDiagnosticSummary(), path resolution tracking, TURN caching in PATH B/C
- `src/services/MessagingService.ts` - ColdStartCoordinator.isHandled duplicate suppression in offer handler, cold start notification in call-ended handler

## Decisions Made
- getCachedTurnServers() tries Metered API first (dynamic per-user creds), falls back to static TURN_USERNAME/TURN_CREDENTIAL env vars
- push.js prefers callData.turnServers from index.js (may be Metered API creds) over its own env var construction for richer TURN coverage
- When VoIP payload exceeds 4500 bytes, SDP is removed (not TURN servers) since SDP is larger and can be retrieved via WebSocket get-call-state fallback
- Made WebSocket message handler async to support await getCachedTurnServers() in get-call-state case

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is wired with real data sources.

## Next Phase Readiness
- All 3 plans in phase 20 are now complete
- Cold start call flow has: coordinator extraction (plan 01), SDP retrieval hardening (plan 02), pipeline hardening + diagnostics (plan 03)
- TURN servers are available in both cold start PATH A (VoIP push) and PATH B (WebSocket get-call-state)
- Diagnostic logging enables easy debugging of cold start failures via [ColdStart] log prefix

## Self-Check: PASSED

All files exist. All commits verified (942efba, 6dadcd7).

---
*Phase: 20-cold-start-call-flow-repair*
*Completed: 2026-03-30*
