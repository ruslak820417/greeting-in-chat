# QRChat Build 300 — LiveKit Migration QA Checklist

## Simulator (verified)
- [x] App launches without crash
- [x] Messages send/receive (P2P data channel works with @livekit/react-native-webrtc)
- [x] Outgoing call connects to LiveKit Room (timer starts)
- [x] Call button doesn't crash

## iPhone Physical (pending — test tomorrow)
- [ ] Warm call (both apps open) → audio works
- [ ] Video call → camera works → switch front/back
- [ ] Mute/unmute during call
- [ ] Speaker toggle
- [ ] Background call → CallKit appears → Answer → audio
- [ ] COLD START (kill app → call → CallKit → Answer → audio)
- [ ] Call-ended propagation (one side hangs up → other side ends)
- [ ] Messages text between phones (regression)
- [ ] Push notifications for messages (regression)
- [ ] Online/offline status updates (regression)
- [ ] Contact request/accept flow (regression)
- [ ] Reinstall app → cold start call → works

## Build Verification
- [x] `npx tsc --noEmit` — zero errors
- [ ] `npx jest --passWithNoTests` — tests pass
- [x] iOS bundle builds successfully
- [x] No forbidden files modified
- [x] Build number = 300
