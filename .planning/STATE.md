# Project State

## Current Position
- **Phase:** 20 -- Cold Start Call Flow Repair
- **Current Plan:** 3 of 3
- **Status:** PHASE_COMPLETE
- **Build:** 99 (v4.3.0+)

## Progress
- Plan 20-01: COMPLETE (ColdStartCoordinator extraction)
- Plan 20-02: COMPLETE (Audio session lifecycle fix)
- Plan 20-03: COMPLETE (SDP pipeline hardening + diagnostics)

## Decisions
- Cold start call flow uses 3-path coordinator (VoIP push, WebSocket get-call-state, pending queue)
- CallKit integration via react-native-callkeep
- Audio session bridged via RTCAudioBridge native module
- SDP stored in UserDefaults by native VoIP push handler (AppDelegate.swift)
- Global `__coldStartCall` state set in index.js for earliest possible capture
- ColdStartCoordinator singleton owns all cold start state -- replaces scattered global state
- Lazy require() in ColdStartCoordinator to avoid circular imports
- Backward-compat global.__coldStartCall proxy delegates to ColdStartCoordinator getters
- Use ColdStartCoordinator.hasAnswer (boolean) instead of .answerUUID for isColdStartIncoming check
- Clear cold start audio state after re-notification to prevent stale state on subsequent calls
- RTCAudioBridge native module and AppDelegate.swift confirmed correct -- no changes needed
- getCachedTurnServers() with 1-hour TTL cache for consistent TURN delivery across push and WebSocket
- push.js prefers callData.turnServers from getCachedTurnServers() over static env var lookup
- VoIP payload size check removes SDP (not TURN) when over 4500 bytes
- Duplicate offer suppression via ColdStartCoordinator.isHandled in MessagingService offer handler

## Known Issues
- PendingVoIPCall was consumed destructively (fixed build 98)
- answerUUID cleared before CallScreen mounted (fixed build 98)
- iPhone 11 auth signature failure (separate issue, not cold-start related)
- Speaker button doesn't work on iPhone 11 (separate issue)

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 20    | 01   | 8min     | 2     | 6     |
| 20    | 02   | 2min     | 2     | 2     |
| 20    | 03   | 5min     | 2     | 4     |

## Last Session
- **Stopped At:** Completed 20-03-PLAN.md
- **Timestamp:** 2026-03-30T05:54:36Z
