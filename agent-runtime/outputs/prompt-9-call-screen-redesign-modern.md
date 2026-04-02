# PROMPT: Redesign CallScreen Connected State — WhatsApp-Style Compact Layout

## TARGET FILE
`/Users/ruslanconstantinovici/QRChat/src/screens/CallScreen.tsx`

(Also located at `/Users/ruslanconstantinovici/QRChat-Audio/src/screens/CallScreen.tsx` — use whichever is the active working copy.)

## OBJECTIVE
When a call transitions from `connecting`/`ringing` to `connected`, animate the UI into a compact, non-intrusive layout inspired by WhatsApp's active call screen:
- Control buttons (Mute, Speaker, Video) shrink and stack vertically in the bottom-left
- End Call button shrinks to a small red circle in the bottom-right
- Timer + quality indicator move to a top-left pill
- Contact name hides
- Avatar section hides (already hidden during video; now also hidden during connected audio)
- Tapping the minimized controls temporarily expands them back to full size

**CRITICAL: Do NOT modify any call logic, WebRTC, audio, signaling, InCallManager, CallKit, or ColdStartCoordinator code. ONLY change layout, styles, and animations.**

---

## CURRENT FILE STRUCTURE (for orientation)

The file is ~1322 lines. Here is the structure:

- **Lines 1-33**: Imports (React, RN, Animated, Easing, WebRTCManager, SignalingClient, etc.)
- **Lines 35-41**: Component declaration, hooks (useTheme, useTranslation, useSafeAreaInsets), route params destructuring
- **Lines 42-61**: State declarations (`isMuted`, `isSpeaker`, `callStatus`, `callDuration`, `localStream`, `remoteStream`, `callQuality`, `isVideoEnabled`, `isFrontCamera`, `remoteVideoEnabled`) and refs (`timerRef`, `durationRef`, `endedRef`, etc.)
- **Lines 62-71**: `statusFade` Animated.Value and its useEffect
- **Lines 73-103**: Ringback tone useEffect
- **Lines 106-140**: `finishAndGoBack()` — call cleanup function
- **Lines 142-213**: Main setup useEffect (event listeners, cleanup)
- **Lines 215-239**: `startConnectedTimer()` — sets callStatus to 'connected', starts 1s interval timer
- **Lines 241-440**: `startCall()` — WebRTC setup, getUserMedia, answer/start call
- **Lines 442-491**: `saveCallLog()` — saves call log to DB
- **Lines 493-546**: Toggle handlers (`endCall`, `toggleMute`, `applySpeaker`, `toggleSpeaker`, `handleToggleVideo`, `handleFlipCamera`, `formatDuration`)
- **Lines 548-578**: Aurora animation Animated.Value declarations (ripples, ringRotation, btnScales, statusBreath, screenOpacity, connectedOpacity)
- **Lines 579-586**: Screen entry fade useEffect
- **Lines 588-639**: Ripple animation useEffect
- **Lines 641-655**: Status breathing animation useEffect
- **Lines 657-665**: `animatePress` callback
- **Lines 667-673**: `ringRotationInterp`, `hasRemoteVideo`, `hasLocalVideo`
- **Lines 676-921**: JSX return — the entire UI:
  - Lines 677-681: Container + background layers
  - Lines 683-696: Aurora orbs + remote video
  - Lines 698-710: Dark overlay + local video PiP
  - Lines 712-726: TOP AREA (encrypted badge, video badge)
  - Lines 728-836: CENTER AREA (avatar, name, status/timer, quality, video waiting)
  - Lines 838-919: BOTTOM CONTROLS (controlsPanel, controlsRow, flipCamera, hangup)
- **Lines 924-1295**: StyleSheet.create — all styles
- **Lines 1297-1322**: ErrorBoundary wrapper + default export

---

## STEP 1: ADD ANIMATED.VALUE DECLARATIONS

**Location:** After the existing `connectedOpacity` declaration (line 577). Insert these new declarations:

```tsx
// ─── Connected compact layout animations ───
const compactProgress = useRef(new Animated.Value(0)).current; // 0 = full layout, 1 = compact
const controlsExpandTimer = useRef<any>(null); // auto-collapse timer after tap
```

`compactProgress` is the master animation driver. All layout interpolations derive from this single value (0 = ringing/connecting full layout, 1 = connected compact layout).

---

## STEP 2: ADD THE COMPACT TRANSITION TRIGGER

**Location:** Add this `useEffect` directly after the existing ripple animation `useEffect` (after the block ending at line 639):

```tsx
// ─── Animate to compact layout when connected ───
useEffect(() => {
  if (callStatus === 'connected') {
    Animated.timing(compactProgress, {
      toValue: 1,
      duration: 400,
      easing: Easing.inOut(Easing.ease),
      useNativeDriver: false, // We need layout animations (width, height, borderRadius)
    }).start();
  } else if (callStatus === 'ended') {
    // Keep compact on ended — no snap back
  } else {
    // Reset to full layout for reconnecting or if call drops back to ringing
    Animated.timing(compactProgress, {
      toValue: 0,
      duration: 300,
      easing: Easing.inOut(Easing.ease),
      useNativeDriver: false,
    }).start();
  }
}, [callStatus]);
```

**Why `useNativeDriver: false`?** We animate layout properties (`width`, `height`, `borderRadius`, `left`, `bottom`) which cannot use the native driver. This is acceptable because this animation runs exactly once at connect time (not continuously).

---

## STEP 3: ADD THE "TAP TO EXPAND" HANDLER

**Location:** Add this function after the `animatePress` callback (after line 665):

```tsx
// ─── Tap minimized controls to temporarily expand ───
const expandControlsTemporarily = useCallback(() => {
  if (callStatus !== 'connected') return;
  clearTimeout(controlsExpandTimer.current);
  Animated.timing(compactProgress, {
    toValue: 0,
    duration: 250,
    easing: Easing.out(Easing.ease),
    useNativeDriver: false,
  }).start();
  // Auto-collapse after 3 seconds
  controlsExpandTimer.current = setTimeout(() => {
    Animated.timing(compactProgress, {
      toValue: 1,
      duration: 350,
      easing: Easing.inOut(Easing.ease),
      useNativeDriver: false,
    }).start();
  }, 3000);
}, [callStatus]);
```

**Also:** Add cleanup for the timer in the existing cleanup `useEffect` return function (inside the block starting at line 188). Add this line alongside the other `clearTimeout` calls:

```tsx
clearTimeout(controlsExpandTimer.current);
```

---

## STEP 4: DEFINE ANIMATED INTERPOLATIONS

**Location:** Add these interpolations right after the `ringRotationInterp` declaration (line 667-670), BEFORE the `hasRemoteVideo` line:

```tsx
// ─── Compact layout interpolations ───

// Center area (avatar + name): visible → hidden
const centerAreaOpacity = compactProgress.interpolate({
  inputRange: [0, 0.5],
  outputRange: [1, 0],
  extrapolate: 'clamp',
});

const centerAreaScale = compactProgress.interpolate({
  inputRange: [0, 1],
  outputRange: [1, 0.85],
  extrapolate: 'clamp',
});

// Top timer pill: hidden → visible (appears as center fades)
const timerPillOpacity = compactProgress.interpolate({
  inputRange: [0.4, 1],
  outputRange: [0, 1],
  extrapolate: 'clamp',
});

const timerPillTranslateY = compactProgress.interpolate({
  inputRange: [0.4, 1],
  outputRange: [-10, 0],
  extrapolate: 'clamp',
});

// Controls panel background: visible → hidden
const panelBgOpacity = compactProgress.interpolate({
  inputRange: [0, 0.5],
  outputRange: [1, 0],
  extrapolate: 'clamp',
});

// Control button labels: visible → hidden (disappear early)
const controlLabelOpacity = compactProgress.interpolate({
  inputRange: [0, 0.3],
  outputRange: [1, 0],
  extrapolate: 'clamp',
});

// Overall controls opacity in compact mode (slightly dimmed)
const compactControlsOpacity = compactProgress.interpolate({
  inputRange: [0, 1],
  outputRange: [1, 0.85],
});

// Hangup text opacity: visible → hidden
const hangupTextOpacity = compactProgress.interpolate({
  inputRange: [0, 0.4],
  outputRange: [1, 0],
  extrapolate: 'clamp',
});

// Control button size: 64px → 40px
const controlBtnSize = compactProgress.interpolate({
  inputRange: [0, 1],
  outputRange: [64, 40],
});

const controlBtnBorderRadius = compactProgress.interpolate({
  inputRange: [0, 1],
  outputRange: [32, 20],
});

// Hangup button: full pill → 56px circle
const hangupHeight = compactProgress.interpolate({
  inputRange: [0, 1],
  outputRange: [72, 56],
});

const hangupBorderRadius = compactProgress.interpolate({
  inputRange: [0, 1],
  outputRange: [36, 28],
});
```

---

## STEP 5: REPLACE THE TOP AREA JSX

**Find** the existing block (lines ~712-726):
```tsx
{/* ═══ TOP AREA — Status info ═══ */}
<View style={[styles.topArea, { paddingTop: insets.top + 20 }]}>
  ...entire topArea block...
</View>
```

**Replace with:**
```tsx
{/* ═══ TOP AREA — Status info + Connected Timer Pill ═══ */}
<View style={[styles.topArea, { paddingTop: insets.top + 20 }]}>
  {/* Encrypted indicator — always visible */}
  <View style={styles.encryptedBadge}>
    <Ionicons name="lock-closed" size={12} color="rgba(255,255,255,0.5)" />
    <Text style={styles.encryptedText}>{t('call.e2eEncrypted')}</Text>
  </View>

  {isVideo && callStatus !== 'ended' && (
    <View style={styles.callTypeBadge}>
      <Ionicons name="videocam" size={13} color={TC.primary} />
      <Text style={[styles.callTypeText, { color: TC.primary }]}>Video</Text>
    </View>
  )}

  {/* Connected: timer pill — aligned left under status bar */}
  {callStatus === 'connected' && (
    <Animated.View style={[styles.timerPill, {
      opacity: timerPillOpacity,
      transform: [{ translateY: timerPillTranslateY }],
    }]}>
      <Text style={styles.timerPillText}>
        {formatDuration(callDuration)}
      </Text>
      {callQuality && (
        <>
          <View style={[styles.timerPillDot, {
            backgroundColor: callQuality === 'good' ? '#34C759' : callQuality === 'fair' ? '#FFD60A' : '#FF3B30',
          }]} />
          <Text style={styles.timerPillQuality}>
            {callQuality === 'good' ? 'Good' : callQuality === 'fair' ? 'Fair' : 'Poor'}
          </Text>
        </>
      )}
    </Animated.View>
  )}
</View>
```

---

## STEP 6: REPLACE THE CENTER AREA JSX

**Find** the existing block (lines ~728-836):
```tsx
{/* ═══ CENTER AREA — Avatar + Info ═══ */}
<View style={[styles.centerArea, hasRemoteVideo && styles.centerAreaOnVideo]}>
  ...entire centerArea block...
</View>
```

**Replace with:**
```tsx
{/* ═══ CENTER AREA — Avatar + Info (fades out when connected compact) ═══ */}
<Animated.View style={[
  styles.centerArea,
  hasRemoteVideo && styles.centerAreaOnVideo,
  {
    opacity: centerAreaOpacity,
    transform: [{ scale: centerAreaScale }],
  },
]}>
  {/* Avatar with aurora ring */}
  {!hasRemoteVideo && callStatus !== 'ended' && (
    <View style={styles.avatarContainer}>
      {/* Ripple rings */}
      <Animated.View style={[styles.rippleRing, {
        borderColor: TC.primary,
        transform: [{ scale: ripple1Scale }],
        opacity: ripple1Opacity,
      }]} />
      <Animated.View style={[styles.rippleRing, {
        borderColor: TC.primary,
        transform: [{ scale: ripple2Scale }],
        opacity: ripple2Opacity,
      }]} />
      <Animated.View style={[styles.rippleRing, {
        borderColor: TC.primary,
        transform: [{ scale: ripple3Scale }],
        opacity: ripple3Opacity,
      }]} />

      {/* Connected: steady rotating ring */}
      {callStatus === 'connected' && (
        <Animated.View style={[styles.connectedRing, {
          borderColor: TC.primary,
          opacity: connectedOpacity,
          transform: [{ rotate: ringRotationInterp }],
        }]}>
          <View style={[styles.connectedRingArc, { backgroundColor: TC.primary }]} />
        </Animated.View>
      )}

      {/* Outer glow */}
      <View style={[styles.avatarGlow, {
        backgroundColor: TC.primary,
        shadowColor: TC.primary,
      }]} />

      {/* Avatar circle */}
      <View style={[styles.avatar, { backgroundColor: TC.primary }]}>
        <Text style={styles.avatarText}>
          {(contactName || '?')[0].toUpperCase()}
        </Text>
      </View>
    </View>
  )}

  {/* Ended state */}
  {callStatus === 'ended' && !hasRemoteVideo && (
    <View style={styles.endedContainer}>
      <View style={[styles.endedIcon, { borderColor: 'rgba(255,255,255,0.15)' }]}>
        <Ionicons name="checkmark" size={40} color="rgba(255,255,255,0.6)" />
      </View>
    </View>
  )}

  {/* Contact name */}
  <Text
    style={[styles.contactName, hasRemoteVideo && styles.contactNameOnVideo]}
    numberOfLines={1}
    accessibilityLabel={`Call with ${contactName}`}
  >
    {contactName}
  </Text>

  {/* Status / Timer — CENTER display for non-connected states */}
  <Animated.View style={{ opacity: statusFade }}>
    {callStatus === 'connected' ? (
      /* Timer moved to top pill in connected state — keep invisible placeholder for smooth fade */
      <View style={{ alignItems: 'center', opacity: 0 }}>
        <Text style={styles.timerText}>{formatDuration(callDuration)}</Text>
      </View>
    ) : callStatus === 'ended' ? (
      <Text style={styles.endedStatusText}>{t('call.ended')}</Text>
    ) : callStatus === 'reconnecting' ? (
      <View style={styles.reconnectingRow}>
        <ActivityIndicator size="small" color="rgba(255,255,255,0.8)" />
        <Text style={styles.reconnectingText}>{t('call.reconnecting')}</Text>
      </View>
    ) : (
      <Animated.Text style={[
        styles.statusText,
        hasRemoteVideo && styles.statusOnVideo,
        { opacity: statusBreath },
      ]}>
        {callStatus === 'ringing' ? t('call.ringing') : t('call.connecting')}
      </Animated.Text>
    )}
  </Animated.View>

  {/* Video waiting indicator */}
  {isVideo && !hasRemoteVideo && callStatus !== 'ended' && (
    <View style={styles.videoWaitingRow}>
      <Ionicons name="videocam-outline" size={15} color={TC.primary} />
      <Text style={[styles.videoWaitingText, { color: TC.primary }]}>{t('call.videoWaiting')}</Text>
    </View>
  )}
</Animated.View>
```

**KEY CHANGE:** The outer `<View>` is now `<Animated.View>` with `opacity: centerAreaOpacity` and `transform: [{ scale: centerAreaScale }]`. This fades out + slightly scales down the entire center content when the call connects.

---

## STEP 7: REPLACE THE BOTTOM CONTROLS JSX

**Find** the existing block (lines ~838-919):
```tsx
{/* ═══ BOTTOM AREA — Controls Panel ═══ */}
<View style={[styles.controlsPanel, { paddingBottom: Math.max(insets.bottom, 20) + 16 }]}>
  ...entire controlsPanel content...
</View>
```

**Replace with this conditional render:**

```tsx
{/* ═══ BOTTOM AREA — Controls ═══ */}
{callStatus === 'connected' ? (
  /* ──── COMPACT CONNECTED LAYOUT ──── */
  <Animated.View
    style={[styles.compactControlsContainer, {
      paddingBottom: Math.max(insets.bottom, 20) + 8,
      opacity: compactControlsOpacity,
    }]}
  >
    {/* Left group: Mute, Speaker, Video — stacked vertically */}
    <TouchableOpacity
      activeOpacity={1}
      onPress={expandControlsTemporarily}
      style={styles.compactLeftGroup}
    >
      {/* Mute */}
      <Animated.View style={{ transform: [{ scale: btnScales.mute }] }}>
        <TouchableOpacity
          style={[styles.compactBtn, isMuted && styles.compactBtnActive]}
          onPress={() => { animatePress('mute'); toggleMute(); }}
          activeOpacity={0.7}
          accessibilityLabel={isMuted ? "Unmute microphone" : "Mute microphone"}
          accessibilityRole="button"
          accessibilityState={{ selected: isMuted }}
        >
          <Ionicons name={isMuted ? 'mic-off' : 'mic-outline'} size={18} color="#fff" />
        </TouchableOpacity>
      </Animated.View>

      {/* Speaker */}
      <Animated.View style={{ transform: [{ scale: btnScales.speaker }] }}>
        <TouchableOpacity
          style={[styles.compactBtn, isSpeaker && styles.compactBtnActive]}
          onPress={() => { animatePress('speaker'); toggleSpeaker(); }}
          activeOpacity={0.7}
          accessibilityLabel={isSpeaker ? "Disable speaker" : "Enable speaker"}
          accessibilityRole="button"
          accessibilityState={{ selected: isSpeaker }}
        >
          <Ionicons name={isSpeaker ? 'volume-high' : 'volume-medium-outline'} size={18} color="#fff" />
        </TouchableOpacity>
      </Animated.View>

      {/* Video toggle */}
      <Animated.View style={{ transform: [{ scale: btnScales.video }] }}>
        <TouchableOpacity
          style={[styles.compactBtn, isVideoEnabled && styles.compactBtnActive]}
          onPress={() => { animatePress('video'); handleToggleVideo(); }}
          activeOpacity={0.7}
          accessibilityLabel={isVideoEnabled ? "Turn off camera" : "Turn on camera"}
          accessibilityRole="button"
          accessibilityState={{ selected: isVideoEnabled }}
        >
          <Ionicons name={isVideoEnabled ? 'videocam' : 'videocam-off-outline'} size={18} color="#fff" />
        </TouchableOpacity>
      </Animated.View>

      {/* Flip camera — only when video is active */}
      {isVideoEnabled && (
        <TouchableOpacity
          style={styles.compactBtn}
          onPress={handleFlipCamera}
          activeOpacity={0.7}
          accessibilityLabel="Flip camera"
          accessibilityRole="button"
        >
          <Ionicons name="camera-reverse-outline" size={18} color="#fff" />
        </TouchableOpacity>
      )}
    </TouchableOpacity>

    {/* Right: small red hangup circle */}
    <Animated.View style={{ transform: [{ scale: btnScales.hangup }] }}>
      <TouchableOpacity
        style={styles.compactHangupBtn}
        onPress={() => { animatePress('hangup'); endCall(); }}
        activeOpacity={0.8}
        accessibilityLabel="End call"
        accessibilityRole="button"
      >
        <Ionicons name="call" size={24} color="#fff" style={{ transform: [{ rotate: '135deg' }] }} />
      </TouchableOpacity>
    </Animated.View>
  </Animated.View>
) : (
  /* ──── FULL LAYOUT (ringing, connecting, reconnecting, ended) ──── */
  <View style={[styles.controlsPanel, { paddingBottom: Math.max(insets.bottom, 20) + 16 }]}>
    {/* Glassmorphism panel background */}
    <View style={styles.controlsPanelBg} />

    {/* Row 1: Mute | Speaker | Video toggle */}
    <View style={styles.controlsRow}>
      {/* Mute */}
      <Animated.View style={[styles.btnWrapper, { transform: [{ scale: btnScales.mute }] }]}>
        <TouchableOpacity
          style={[styles.btnGlass, isMuted && styles.btnGlassActive]}
          onPress={() => { animatePress('mute'); toggleMute(); }}
          activeOpacity={0.7}
          accessibilityLabel={isMuted ? "Unmute microphone" : "Mute microphone"}
          accessibilityRole="button"
          accessibilityState={{ selected: isMuted }}
        >
          <Ionicons name={isMuted ? 'mic-off' : 'mic-outline'} size={26} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.btnLabel}>{isMuted ? t('call.unmute') : t('call.mute')}</Text>
      </Animated.View>

      {/* Speaker */}
      <Animated.View style={[styles.btnWrapper, { transform: [{ scale: btnScales.speaker }] }]}>
        <TouchableOpacity
          style={[styles.btnGlass, isSpeaker && styles.btnGlassActive]}
          onPress={() => { animatePress('speaker'); toggleSpeaker(); }}
          activeOpacity={0.7}
          accessibilityLabel={isSpeaker ? "Disable speaker" : "Enable speaker"}
          accessibilityRole="button"
          accessibilityState={{ selected: isSpeaker }}
        >
          <Ionicons name={isSpeaker ? 'volume-high' : 'volume-medium-outline'} size={26} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.btnLabel}>{isSpeaker ? t('call.speaker') : t('call.earpiece')}</Text>
      </Animated.View>

      {/* Video toggle */}
      <Animated.View style={[styles.btnWrapper, { transform: [{ scale: btnScales.video }] }]}>
        <TouchableOpacity
          style={[styles.btnGlass, isVideoEnabled && styles.btnGlassActive]}
          onPress={() => { animatePress('video'); handleToggleVideo(); }}
          activeOpacity={0.7}
          accessibilityLabel={isVideoEnabled ? "Turn off camera" : "Turn on camera"}
          accessibilityRole="button"
          accessibilityState={{ selected: isVideoEnabled }}
        >
          <Ionicons name={isVideoEnabled ? 'videocam' : 'videocam-off-outline'} size={26} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.btnLabel}>{isVideoEnabled ? 'Video' : 'Video'}</Text>
      </Animated.View>
    </View>

    {/* Row 2: Flip camera (only visible when local video active) */}
    {isVideoEnabled && (
      <View style={styles.flipCameraRow}>
        <TouchableOpacity
          style={styles.btnGlass}
          onPress={handleFlipCamera}
          activeOpacity={0.7}
          accessibilityLabel="Flip camera"
          accessibilityRole="button"
        >
          <Ionicons name="camera-reverse-outline" size={24} color="#fff" />
        </TouchableOpacity>
      </View>
    )}

    {/* Hang up */}
    <Animated.View style={[styles.hangupRow, { transform: [{ scale: btnScales.hangup }] }]}>
      <TouchableOpacity
        style={[styles.hangupBtn, { shadowColor: TC.error }]}
        onPress={() => { animatePress('hangup'); endCall(); }}
        activeOpacity={0.8}
        accessibilityLabel="End call"
        accessibilityRole="button"
      >
        <View style={styles.hangupBtnInner}>
          <Ionicons name="call" size={28} color="#fff" style={{ transform: [{ rotate: '135deg' }] }} />
          <Text style={styles.hangupBtnText}>End Call</Text>
        </View>
      </TouchableOpacity>
    </Animated.View>
  </View>
)}
```

---

## STEP 8: ADD NEW STYLES TO STYLESHEET

**Location:** Add these at the end of the `StyleSheet.create({})` object, right before the closing `});` (before line 1295). Do NOT delete any existing styles.

```tsx
// ─── Timer Pill (top-left, connected state) ───
timerPill: {
  flexDirection: 'row',
  alignItems: 'center',
  alignSelf: 'flex-start',
  paddingHorizontal: 14,
  paddingVertical: 7,
  borderRadius: 16,
  backgroundColor: 'rgba(0,0,0,0.35)',
  borderWidth: 1,
  borderColor: 'rgba(255,255,255,0.08)',
  gap: 6,
  marginTop: 4,
  marginLeft: -8,  // counteract parent paddingHorizontal to push left
},
timerPillText: {
  fontSize: 15,
  fontWeight: '600',
  color: '#FFFFFF',
  fontVariant: ['tabular-nums'],
  letterSpacing: 1,
},
timerPillDot: {
  width: 7,
  height: 7,
  borderRadius: 3.5,
},
timerPillQuality: {
  fontSize: 11,
  color: 'rgba(255,255,255,0.55)',
  fontWeight: '500',
},

// ─── Compact connected layout ───
compactControlsContainer: {
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  flexDirection: 'row',
  justifyContent: 'space-between',
  alignItems: 'flex-end',
  paddingHorizontal: 20,
},
compactLeftGroup: {
  flexDirection: 'column',
  alignItems: 'center',
  gap: 10,
},
compactBtn: {
  width: 40,
  height: 40,
  borderRadius: 20,
  backgroundColor: 'rgba(255, 255, 255, 0.12)',
  borderWidth: 1,
  borderColor: 'rgba(255, 255, 255, 0.1)',
  alignItems: 'center',
  justifyContent: 'center',
},
compactBtnActive: {
  backgroundColor: 'rgba(255, 255, 255, 0.3)',
  borderColor: 'rgba(255, 255, 255, 0.25)',
},
compactHangupBtn: {
  width: 56,
  height: 56,
  borderRadius: 28,
  backgroundColor: '#FF3B30',
  alignItems: 'center',
  justifyContent: 'center',
  shadowColor: '#FF3B30',
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.5,
  shadowRadius: 12,
  elevation: 8,
},
```

---

## STEP 9: HANDLE RECONNECTING STATE

When `callStatus` changes from `connected` to `reconnecting`, the `compactProgress` useEffect (Step 2) resets it to `0`, which:
- Fades the center area back in (shows reconnecting spinner + text)
- Returns controls to full layout

When `callStatus` goes back to `connected` (ICE reconnected), `compactProgress` animates to `1` again and the compact layout returns. **No additional code needed for this.**

---

## STEP 10: HANDLE "ENDED" STATE AFTER COMPACT

When `callStatus` is `ended`, the existing code already shows the ended screen for ~800ms before navigating back. Since `compactProgress` stays at `1` during `ended` (see Step 2 — no-op for ended), and the center area has `opacity: centerAreaOpacity` (which is `0` at `compactProgress=1`), you need one small adjustment:

**In the center area JSX (Step 6), the ended state needs to be visible.** The current code already handles this because the `callStatus === 'ended'` check is inside the `Animated.View`, but the entire view fades out. Fix: add a special case where ended state bypasses the fade.

**Option A (simplest):** Move the ended content OUTSIDE the Animated.View center area. Add it as a sibling:

Right after the `</Animated.View>` that closes the center area (Step 6), add:

```tsx
{/* Ended overlay — renders above the faded center area */}
{callStatus === 'ended' && !hasRemoteVideo && (
  <View style={[styles.centerArea, { position: 'absolute', top: 0, bottom: 0, left: 0, right: 0 }]}>
    <View style={styles.endedContainer}>
      <View style={[styles.endedIcon, { borderColor: 'rgba(255,255,255,0.15)' }]}>
        <Ionicons name="checkmark" size={40} color="rgba(255,255,255,0.6)" />
      </View>
    </View>
    <Text style={styles.contactName} numberOfLines={1}>{contactName}</Text>
    <Text style={styles.endedStatusText}>{t('call.ended')}</Text>
  </View>
)}
```

---

## COMPLETE IMPLEMENTATION CHECKLIST

- [ ] Added `compactProgress` Animated.Value ref (Step 1)
- [ ] Added `controlsExpandTimer` ref (Step 1)
- [ ] Added compact transition `useEffect` triggered by `callStatus` (Step 2)
- [ ] Added `expandControlsTemporarily` callback (Step 3)
- [ ] Added `clearTimeout(controlsExpandTimer.current)` to cleanup (Step 3)
- [ ] Added all interpolation variables from `compactProgress` (Step 4)
- [ ] Updated TOP AREA JSX with timer pill (Step 5)
- [ ] Replaced CENTER AREA outer `View` with `Animated.View` (Step 6)
- [ ] Replaced BOTTOM CONTROLS with conditional compact/full render (Step 7)
- [ ] Added all new styles to StyleSheet (Step 8)
- [ ] Verified reconnecting state works (Step 9)
- [ ] Added ended state overlay (Step 10)
- [ ] Did NOT modify any call logic, WebRTC, signaling, or audio code
- [ ] Did NOT delete any existing styles (only added new ones)
- [ ] All existing functionality preserved: mute, speaker, video toggle, camera flip, end call
- [ ] All accessibility labels preserved on all buttons

---

## VISUAL REFERENCE — Connected State Layout

```
+------------------------------------------+
| [lock] E2E Encrypted                    |
| [0:07 * Good]              [Local PiP]  |
|                                          |
|                                          |
|           (empty / remote video)         |
|                                          |
|                                          |
|                                          |
| [Mic]                                   |
| [Spk]                          [Hangup] |
| [Vid]                           (red)   |
+------------------------------------------+
```

- **Top-left:** Semi-transparent pill with timer (15px tabular-nums) + quality dot + quality label
- **Bottom-left:** Vertically stacked 40px translucent control circles (10px gap between them)
- **Bottom-right:** 56px red circle with rotated phone icon
- **Center:** Empty space (audio) or full-screen remote video

---

## TESTING CHECKLIST

1. **Audio call: ringing state** — Verify original full layout: large avatar, name, ripple rings, large centered buttons, full-width red hangup pill
2. **Audio call: connect transition** — Verify 400ms animation: avatar+name fades out, timer pill fades in top-left, buttons morph to compact bottom-left, hangup shrinks to bottom-right circle
3. **Tap compact controls** — Verify controls expand to full size for 3 seconds, then auto-collapse
4. **Mute/Speaker/Video** — Verify all three toggles work correctly in compact mode (state persists, icon updates, active style applies)
5. **Video call connect** — Verify compact controls overlay on top of remote video, local PiP stays top-right
6. **Flip camera in compact** — Verify fourth button appears in compact left stack when video enabled
7. **End call from compact** — Verify red circle triggers `endCall()` correctly, ended screen appears with checkmark and name
8. **Reconnecting** — Verify full layout returns with reconnecting indicator, then compact resumes when reconnected
9. **Timer accuracy** — Verify top-left pill timer increments every second and matches actual call duration
10. **Quality indicator** — Verify dot color changes (green/yellow/red) and label updates in pill
