# Project State

## Current Position
- **Phase:** 20 — Cold Start Call Flow Repair
- **Status:** PLANNING
- **Build:** 99 (v4.3.0+)

## Decisions
- Cold start call flow uses 3-path coordinator (VoIP push, WebSocket get-call-state, pending queue)
- CallKit integration via react-native-callkeep
- Audio session bridged via RTCAudioBridge native module
- SDP stored in UserDefaults by native VoIP push handler (AppDelegate.swift)
- Global `__coldStartCall` state set in index.js for earliest possible capture

## Known Issues
- PendingVoIPCall was consumed destructively (fixed build 98)
- answerUUID cleared before CallScreen mounted (fixed build 98)
- iPhone 11 auth signature failure (separate issue, not cold-start related)
- Speaker button doesn't work on iPhone 11 (separate issue)
- Cold start coordinator complexity (~200 lines, 3 paths, race conditions)
