# GitHub Pages Setup — QRChat Privacy Policy

## Files Created

- `/docs/privacy.html` — Full Privacy Policy page (responsive, inline styles, QRChat branding)
- `/docs/index.html` — Auto-redirect to privacy.html

## How to Enable GitHub Pages

1. Push the `docs/` folder to the `main` branch on GitHub
2. Go to the repo on GitHub: **Settings > Pages**
3. Under **Source**, select: **Deploy from a branch**
4. Set **Branch** to `main` and **Folder** to `/docs`
5. Click **Save**
6. Wait 1-2 minutes for the first deployment

### Resulting URL

The Privacy Policy will be available at:

```
https://<username>.github.io/QRChat/privacy.html
```

### Using gh CLI (alternative)

```bash
gh api repos/{owner}/{repo}/pages -X POST -f source.branch=main -f source.path=/docs
```

## After Activation

Update the Privacy Policy URL in these locations:

1. **`ios/QRChat/Info.plist`** — line with the privacy URL string
2. **App Store Connect** — App Information > Privacy Policy URL
3. **SettingsScreen** — frontend-engineer should use this URL for the in-app Privacy Policy link

## Placeholders Replaced

- `[developer contact email]` -> `privacy@qrchat.app`
- `[privacy policy URL to be hosted]` -> removed (URL determined after GitHub Pages activation)

## Design Specs

- Background: #fafafa (off-white)
- Text: #1a1a2e (dark navy)
- Accent: #FF6B00 (QRChat orange)
- Max-width: 720px, centered
- Font: system font stack (-apple-system, BlinkMacSystemFont, Segoe UI, Roboto)
- Fully responsive with mobile breakpoint at 480px
- All styles inline (single HTML file, no external dependencies)
