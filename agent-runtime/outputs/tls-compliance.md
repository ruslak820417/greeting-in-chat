# TLS Compliance Report — QRChat Server

**Date:** 2026-03-21
**Author:** backend-engineer

## Architecture

QRChat server runs on **Railway** (railway.app) as a plain HTTP/WS Node.js process.

- **Server code:** `http.createServer(app)` — no application-level TLS
- **Railway config:** `railway.json` — NIXPACKS builder, `node index.js` start command
- **Production URL:** `wss://exciting-success-production-d272.up.railway.app`

## TLS Termination

Railway performs **TLS termination at the edge** via its reverse proxy. This means:

1. **Client → Railway edge:** TLS 1.2 / TLS 1.3 (handled by Railway's infrastructure)
2. **Railway edge → App container:** Plain HTTP/WS (internal network, not exposed)

Railway's edge proxy:
- Supports **TLS 1.3** and TLS 1.2
- Provides automatic SSL certificates (Let's Encrypt)
- Handles certificate rotation automatically
- Forces HTTPS on all `*.up.railway.app` domains

## Client-Side Enforcement

In `src/network/SignalingClient.ts`:
- Production server URL is hardcoded as `wss://` (line 14)
- Domain pinning to `exciting-success-production-d272.up.railway.app` (line 42)
- Validation enforces `wss://` protocol and pinned domain in production (line 59)

## Verification

- The app exclusively uses `wss://` for WebSocket connections
- Railway does NOT allow plain `ws://` connections on public domains
- TLS 1.3 is supported by Railway's edge (GCP-based infrastructure)

## Conclusion

**TLS 1.3: SUPPORTED** via Railway's edge TLS termination.

No changes needed on the server side. The current architecture correctly delegates TLS to Railway's infrastructure, which supports TLS 1.3. The client enforces `wss://` and domain pinning, ensuring all traffic is encrypted in transit.

## Recommendation

No action required. If a custom domain is added in the future, Railway will automatically provision and manage TLS certificates for it as well.
