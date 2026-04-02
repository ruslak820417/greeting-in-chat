---
status: diagnosed
trigger: "Phase 20 ColdStartCoordinator extraction broke ALL messaging, calls, online status in QRChat"
created: 2026-03-30T00:00:00Z
updated: 2026-03-30T00:01:00Z
---

## Current Focus

hypothesis: CONFIRMED -- 3 interacting bugs from incomplete refactoring
test: Traced all code paths through 8 files, verified with git diff
expecting: N/A - root causes found
next_action: Apply fixes per debug report

## Symptoms

expected: Calls appear on receiving device, messages deliver, online/last seen updates, audio/video calls work
actual: Call screen doesn't appear, messages don't arrive, online status doesn't update, audio/video broken - "technical corpse"
errors: TypeError: hasColdStartAnswer is not a function (runtime, unhandled promise rejection)
reproduction: Any call from iPhone 16 to iPhone 11, any message send, any status check
started: After Phase 20 commits (a61d2b1 through 85c44ca), previously worked at Build 83 commit 4e508ac

## Eliminated

- hypothesis: Server-side TURN caching breaks message relay
  evidence: Server changes only affect call-related endpoints (get-call-state, VoIP push). encrypted-message and ping-user handlers unchanged.
  timestamp: 2026-03-30T00:01:00Z

- hypothesis: ColdStartCoordinator circular import breaks initialization
  evidence: All imports use lazy require() inside functions, not top-level. No circular dependency.
  timestamp: 2026-03-30T00:01:00Z

- hypothesis: SDP minification in push.js corrupts call data
  evidence: Minification only strips extmap/rtcp-fb lines, has size validation with fallback. Correct implementation.
  timestamp: 2026-03-30T00:01:00Z

- hypothesis: Async ws.on('message') handler on server breaks message processing
  evidence: Node.js handles async WebSocket handlers correctly. Each message processed independently.
  timestamp: 2026-03-30T00:01:00Z

## Evidence

- timestamp: 2026-03-30T00:00:10Z
  checked: MessagingService.ts line 300
  found: CallKitServiceRef.hasColdStartAnswer() called but method was REMOVED from CallKitService in Phase 20
  implication: Every incoming call offer throws TypeError, call never reaches EventBus.emit('incoming-call')

- timestamp: 2026-03-30T00:00:15Z
  checked: ColdStartCoordinator.reset() callers
  found: reset() method exists at line 406 but has ZERO callers in the entire codebase
  implication: Once handled=true is set, ColdStartCoordinator.isHandled stays true forever, blocking all subsequent calls

- timestamp: 2026-03-30T00:00:20Z
  checked: index.js lines 104-108 (normal event listeners)
  found: onAnswerCall and onEndCall write to ColdStartCoordinator for ALL CallKit events, not just cold start
  implication: Warm call answer/decline sets ColdStartCoordinator.answerUUID/declineUUID, causing next call to be falsely treated as cold start

- timestamp: 2026-03-30T00:00:25Z
  checked: git diff 4e508ac..85c44ca for all 8 files
  found: MessagingService diff only changes call-ended and offer handlers. No changes to encrypted-message, user-status, or message relay code.
  implication: Messages and online status are NOT broken by the code changes. Server changes are all call-related.

- timestamp: 2026-03-30T00:00:30Z
  checked: SignalingClient.emit() implementation (line 442)
  found: Uses forEach() -- async handler rejection does not block other handlers from the same event
  implication: WebRTCManager still receives P2P data channel offers. Only MessagingService call offer path crashes.

## Resolution

root_cause: |
  3 interacting bugs from incomplete Phase 20 refactoring:
  BUG #1: MessagingService.ts:300 calls CallKitService.hasColdStartAnswer() which was REMOVED (dangling reference). Throws TypeError on every incoming call offer.
  BUG #2: ColdStartCoordinator.reset() exists but is NEVER called. Once handled=true, ALL calls permanently blocked.
  BUG #3: index.js normal event listeners write to ColdStartCoordinator for ALL calls (not just cold start), causing warm calls to contaminate cold start state.
fix: |
  1. Replace MessagingService.ts:300 CallKitServiceRef.hasColdStartAnswer() with ColdStartCoordinator.hasAnswer
  2. Remove index.js lines 104-108 (normal event listeners -- redundant with CallKitService.initialize())
  3. Add ColdStartCoordinator.reset() call in CallScreen.finishAndGoBack() and cold start timeout
verification: Pending -- fixes not yet applied
files_changed:
  - src/services/MessagingService.ts
  - index.js
  - src/screens/CallScreen.tsx
  - App.tsx
