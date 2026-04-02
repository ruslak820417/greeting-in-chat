# Frontend Engineer Prompt — 3 Visual Fixes (ChatScreen + CallScreen)

**Target files:**
- `/Users/ruslanconstantinovici/QRChat-Audio/src/screens/ChatScreen.tsx`
- `/Users/ruslanconstantinovici/QRChat-Audio/src/screens/CallScreen.tsx`

**Rules:**
- ONLY modify styles, layout, visual elements
- DO NOT touch call logic, WebRTC, audio, signaling, encryption, or message delivery
- Keep all existing functionality intact
- Test on both simulator and physical device after changes

---

## FIX 1: ChatScreen — Message Bubbles Unreadable at Bottom (Gradient Conflict)

### Problem
The chat uses a full-screen `GradientBackground` (lines 2120-2122) behind all content. Messages at the bottom of the screen blend into the gradient, especially on dark/ember themes where the gradient gets brighter at the bottom. The message bubbles have no backdrop separation from the gradient.

### Solution
Add a semi-transparent backdrop to message bubbles when gradient mode is active, and add a bottom readability scrim over the gradient behind the messages area.

### Change 1A: Add bottom-fade scrim over gradient, behind the FlatList

At **line 2302** in `ChatScreen.tsx`, there is:
```
      {/* Mesaje */}
      <View style={{ flex: 1, position: 'relative' }}>
      <FlatList
```

Replace with:
```
      {/* Mesaje */}
      <View style={{ flex: 1, position: 'relative' }}>
      {/* Bottom readability scrim — darkens gradient behind last messages */}
      {T.useGradient && (
        <View pointerEvents="none" style={{
          position: 'absolute', bottom: 0, left: 0, right: 0, height: 200, zIndex: 0,
        }}>
          <Svg style={StyleSheet.absoluteFill} preserveAspectRatio="none">
            <Defs>
              <SvgGradient id="chatBottomScrim" x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor="#000000" stopOpacity="0" />
                <Stop offset="0.5" stopColor="#000000" stopOpacity="0.15" />
                <Stop offset="1" stopColor="#000000" stopOpacity="0.35" />
              </SvgGradient>
            </Defs>
            <SvgRect x="0" y="0" width="100%" height="100%" fill="url(#chatBottomScrim)" />
          </Svg>
        </View>
      )}
      <FlatList
```

**old_string (exact):**
```
      {/* Mesaje */}
      <View style={{ flex: 1, position: 'relative' }}>
      <FlatList
```

**new_string (exact):**
```
      {/* Mesaje */}
      <View style={{ flex: 1, position: 'relative' }}>
      {/* Bottom readability scrim — darkens gradient behind last messages */}
      {T.useGradient && (
        <View pointerEvents="none" style={{
          position: 'absolute', bottom: 0, left: 0, right: 0, height: 200, zIndex: 0,
        }}>
          <Svg style={StyleSheet.absoluteFill} preserveAspectRatio="none">
            <Defs>
              <SvgGradient id="chatBottomScrim" x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor="#000000" stopOpacity="0" />
                <Stop offset="0.5" stopColor="#000000" stopOpacity="0.15" />
                <Stop offset="1" stopColor="#000000" stopOpacity="0.35" />
              </SvgGradient>
            </Defs>
            <SvgRect x="0" y="0" width="100%" height="100%" fill="url(#chatBottomScrim)" />
          </Svg>
        </View>
      )}
      <FlatList
```

### Change 1B: Add backdrop blur effect to message bubbles in gradient mode

At **line 330-336** in `ChatScreen.tsx`, the bubble style assembly is:

**old_string (exact):**
```
          style={[
            styles.messageBubble,
            isMine ? styles.myMessage : styles.theirMessage,
            item.contentType === 'image' && styles.imageBubble,
            searchResults.has(item.id) && styles.searchHighlight,
            isMine && T.useGradient && { borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)' },
          ]}
```

**new_string (exact):**
```
          style={[
            styles.messageBubble,
            isMine ? styles.myMessage : styles.theirMessage,
            item.contentType === 'image' && styles.imageBubble,
            searchResults.has(item.id) && styles.searchHighlight,
            isMine && T.useGradient && { borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)', backgroundColor: 'rgba(255,255,255,0.13)' },
            !isMine && T.useGradient && { backgroundColor: 'rgba(0,0,0,0.35)', borderColor: 'rgba(255,255,255,0.08)' },
          ]}
```

This gives "their" bubbles a dark semi-transparent backdrop on gradient themes, and reinforces "my" bubbles with a slightly more opaque white tint. Both improve readability against any gradient.

---

## FIX 2: CallScreen — Compact Connected Buttons Barely Visible

### Problem
When the call connects and controls animate to compact (bottom-left), the buttons use `backgroundColor: 'rgba(255, 255, 255, 0.12)'` (line 1500) which is nearly invisible against the dark aurora background. The `compactControlsOpacity` interpolates down to 0.85 (line 732), making it even worse.

### Solution
Increase button background opacity, add shadow, increase icon size, and fix the container opacity.

### Change 2A: Fix compactControlsOpacity — keep it at full 1.0

At **line 731-733** in `CallScreen.tsx`:

**old_string (exact):**
```
  const compactControlsOpacity = compactProgress.interpolate({
    inputRange: [0, 1], outputRange: [1, 0.85],
  });
```

**new_string (exact):**
```
  const compactControlsOpacity = compactProgress.interpolate({
    inputRange: [0, 1], outputRange: [1, 1],
  });
```

### Change 2B: Increase compact button background opacity and size

At **line 1496-1505** in `CallScreen.tsx`:

**old_string (exact):**
```
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
```

**new_string (exact):**
```
  compactBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 4,
  },
```

### Change 2C: Increase active button contrast

At **line 1506-1509** in `CallScreen.tsx`:

**old_string (exact):**
```
  compactBtnActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderColor: 'rgba(255, 255, 255, 0.25)',
  },
```

**new_string (exact):**
```
  compactBtnActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.35)',
    borderColor: 'rgba(255, 255, 255, 0.4)',
  },
```

### Change 2D: Increase icon size from 18 to 22 in compact buttons

There are 4 icon instances in the compact controls section. Replace each one:

**Icon 1 — Mute (line 936):**

old_string:
```
                <Ionicons name={isMuted ? 'mic-off' : 'mic-outline'} size={18} color="#fff" />
              </TouchableOpacity>
            </Animated.View>

            <Animated.View style={{ transform: [{ scale: btnScales.speaker }] }}>
              <TouchableOpacity
                style={[styles.compactBtn, isSpeaker && styles.compactBtnActive]}
```

new_string:
```
                <Ionicons name={isMuted ? 'mic-off' : 'mic-outline'} size={22} color="#fff" />
              </TouchableOpacity>
            </Animated.View>

            <Animated.View style={{ transform: [{ scale: btnScales.speaker }] }}>
              <TouchableOpacity
                style={[styles.compactBtn, isSpeaker && styles.compactBtnActive]}
```

**Icon 2 — Speaker (line 949):**

old_string:
```
                <Ionicons name={isSpeaker ? 'volume-high' : 'volume-medium-outline'} size={18} color="#fff" />
              </TouchableOpacity>
            </Animated.View>

            <Animated.View style={{ transform: [{ scale: btnScales.video }] }}>
              <TouchableOpacity
                style={[styles.compactBtn, isVideoEnabled && styles.compactBtnActive]}
```

new_string:
```
                <Ionicons name={isSpeaker ? 'volume-high' : 'volume-medium-outline'} size={22} color="#fff" />
              </TouchableOpacity>
            </Animated.View>

            <Animated.View style={{ transform: [{ scale: btnScales.video }] }}>
              <TouchableOpacity
                style={[styles.compactBtn, isVideoEnabled && styles.compactBtnActive]}
```

**Icon 3 — Video (line 962):**

old_string:
```
                <Ionicons name={isVideoEnabled ? 'videocam' : 'videocam-off-outline'} size={18} color="#fff" />
```

new_string:
```
                <Ionicons name={isVideoEnabled ? 'videocam' : 'videocam-off-outline'} size={22} color="#fff" />
```

**Icon 4 — Flip camera (line 974):**

old_string:
```
                <Ionicons name="camera-reverse-outline" size={18} color="#fff" />
```

new_string:
```
                <Ionicons name="camera-reverse-outline" size={22} color="#fff" />
```

---

## FIX 3: CallScreen — Show Avatar During Connected Audio Call

### Problem
When an audio call connects, the center area (avatar + contact name + status) fades to `opacity: 0` via `centerAreaOpacity` (line 719-720, inputRange `[0, 0.5]` maps to `[1, 0]`). This leaves a completely empty center during audio calls — only aurora orbs are visible.

### Solution
Add a new centered avatar element that renders OUTSIDE the fading center area, only during connected audio calls (no remote video). This avatar sits between the aurora orbs and the compact controls.

### Change 3A: Add audio call avatar after the center area Animated.View closes

At **line 897** in `CallScreen.tsx`, after the center area `</Animated.View>` and before the ended overlay, find:

**old_string (exact):**
```
      </Animated.View>

      {/* Ended overlay — renders above the faded center area */}
      {callStatus === 'ended' && !hasRemoteVideo && (
```

**new_string (exact):**
```
      </Animated.View>

      {/* ═══ AUDIO CALL AVATAR — centered rounded square during connected audio ═══ */}
      {callStatus === 'connected' && !hasRemoteVideo && (
        <Animated.View
          pointerEvents="none"
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: 0,
            right: 0,
            alignItems: 'center',
            justifyContent: 'center',
            opacity: compactProgress.interpolate({
              inputRange: [0.5, 1],
              outputRange: [0, 1],
              extrapolate: 'clamp',
            }),
          }}
        >
          <View style={{
            width: 120,
            height: 120,
            borderRadius: 24,
            backgroundColor: 'rgba(255,255,255,0.08)',
            borderWidth: 1.5,
            borderColor: 'rgba(255,255,255,0.12)',
            alignItems: 'center',
            justifyContent: 'center',
            shadowColor: '#000',
            shadowOffset: { width: 0, height: 8 },
            shadowOpacity: 0.3,
            shadowRadius: 20,
            elevation: 10,
          }}>
            <View style={{
              width: 110,
              height: 110,
              borderRadius: 20,
              backgroundColor: TC.primary,
              alignItems: 'center',
              justifyContent: 'center',
              opacity: 0.85,
            }}>
              <Text style={{
                fontSize: 48,
                color: '#FFFFFF',
                fontWeight: '700',
                letterSpacing: -1,
              }}>
                {(contactName || '?')[0].toUpperCase()}
              </Text>
            </View>
          </View>
          <Text style={{
            fontSize: 18,
            color: 'rgba(255,255,255,0.7)',
            fontWeight: '600',
            marginTop: 16,
            letterSpacing: 0.3,
          }}>
            {contactName}
          </Text>
        </Animated.View>
      )}

      {/* Ended overlay — renders above the faded center area */}
      {callStatus === 'ended' && !hasRemoteVideo && (
```

### What this does:
- Renders a 120x120 rounded square (`borderRadius: 24`) with a frosted glass outer container
- Inside: a 110x110 rounded square with the theme's primary color at 0.85 opacity
- Shows the contact's first letter (same style as existing avatar, font size 48)
- Fades IN as `compactProgress` goes from 0.5 to 1 (exactly as the original center fades OUT)
- Contact name below the avatar in subtle white
- `pointerEvents="none"` so it does not block the compact controls at bottom-left/right
- Only renders when `callStatus === 'connected'` AND `!hasRemoteVideo` (audio only)
- Position is `absolute` covering the full screen, centered via flexbox — controls at bottom corners are not affected

---

## Summary of Changes

| File | Lines Affected | What Changes |
|------|---------------|--------------|
| ChatScreen.tsx | ~2302 | Add SVG gradient scrim (dark fade at bottom) behind FlatList |
| ChatScreen.tsx | ~330-336 | Add semi-transparent backdrop to bubbles on gradient themes |
| CallScreen.tsx | ~731-733 | Fix compactControlsOpacity to stay at 1.0 |
| CallScreen.tsx | ~1496-1509 | Bigger, darker compact buttons with shadow |
| CallScreen.tsx | ~936, 949, 962, 974 | Icon size 18 -> 22 |
| CallScreen.tsx | ~897 | New audio call avatar block (connected + no video) |

**DO NOT touch:** WebRTC, signaling, CallStateMachine, ColdStartCoordinator, audio routing, encryption, or any call flow logic.
