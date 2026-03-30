# Roadmap

### Phase 20: Cold Start Call Flow Repair

**Goal:** Stabilize and simplify the cold start incoming call flow so that calls reliably connect with audio when the app is woken from a killed state by a VoIP push notification.

**Requirements:** [COLD-01, COLD-02, COLD-03, COLD-04]

**Plans:** 3 plans

Plans:
- [ ] 20-01-PLAN.md -- Consolidate cold start state and extract ColdStartCoordinator module
- [ ] 20-02-PLAN.md -- Fix audio session lifecycle for cold start calls
- [ ] 20-03-PLAN.md -- Harden SDP delivery and add end-to-end cold start logging
