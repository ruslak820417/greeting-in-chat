# PROMPT 7 — Privacy Policy webpage (release-engineer)

**Agent:** release-engineer
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Prioritate:** CRITICA — Apple cere un URL public functional pentru Privacy Policy

---

## Context

Apple App Store cere un URL public si functional catre Privacy Policy. In prezent:
- Textul complet al Privacy Policy exista in: `agent-runtime/outputs/privacy-policy.md` (din proiectul Agent Teams: `/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/privacy-policy.md`)
- Info.plist refera `https://qrchat.app/privacy` dar acest URL probabil nu functioneaza
- SettingsScreen nu are inca link catre Privacy Policy (frontend-engineer il adauga — vezi Prompt 5)

Trebuie:
1. Sa creezi o pagina HTML frumoasa cu textul Privacy Policy
2. Sa o salvezi in repo
3. Sa o hostezi la un URL public

---

## Sarcina 1 — Creeaza pagina HTML cu Privacy Policy

**Output:** `/Users/ruslanconstantinovici/QRChat/docs/privacy.html`

### Cerinte:
- **Responsive** — trebuie sa arate bine pe mobile (utilizatorii vor deschide din app)
- **Stiluri inline** — un singur fisier HTML, fara CSS extern, fara JS extern
- **Design profesional** — fundal curat, font lizibil, spacing aerisit
- **Culorile QRChat** — foloseste accentul portocaliu (#FF6B00) din branding

### Textul sursa:
Copiaza continutul din `/Users/ruslanconstantinovici/Projects/Agent Teams/agent-runtime/outputs/privacy-policy.md` si converteste-l in HTML.

### IMPORTANT — Completeaza placeholder-urile:
In privacy-policy.md exista aceste placeholder-uri care trebuie inlocuite:
- `[developer contact email]` → `privacy@qrchat.app` (sau alt email valid)
- `[privacy policy URL to be hosted]` → URL-ul final unde va fi hostata pagina

### Structura HTML recomandata:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QRChat — Privacy Policy</title>
    <style>
        /* Inline styles */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.7;
            color: #1a1a2e;
            background: #fafafa;
            padding: 0 16px;
        }
        .container { max-width: 720px; margin: 0 auto; padding: 40px 0 80px; }
        h1 { font-size: 28px; color: #FF6B00; margin-bottom: 8px; }
        h2 { font-size: 20px; color: #1a1a2e; margin-top: 36px; margin-bottom: 12px;
             border-bottom: 2px solid #FF6B00; padding-bottom: 6px; }
        h3 { font-size: 16px; margin-top: 20px; margin-bottom: 8px; }
        p { margin-bottom: 12px; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
        th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; }
        th { background: #f5f5f5; font-weight: 600; }
        ul { padding-left: 24px; margin-bottom: 12px; }
        li { margin-bottom: 6px; }
        strong { color: #FF6B00; }
        a { color: #FF6B00; }
        .meta { color: #666; font-size: 14px; margin-bottom: 24px; }
        hr { border: none; border-top: 1px solid #eee; margin: 24px 0; }
        @media (max-width: 480px) {
            body { padding: 0 12px; }
            h1 { font-size: 24px; }
            h2 { font-size: 18px; }
            table { font-size: 12px; }
            th, td { padding: 6px 8px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Converteste tot markdown-ul in HTML aici -->
    </div>
</body>
</html>
```

### Verifica rezultatul:
```bash
# Deschide in browser local
open /Users/ruslanconstantinovici/QRChat/docs/privacy.html
```
- Verifica ca se vede bine pe desktop
- Verifica responsive: in Chrome DevTools, simuleaza iPhone (375px width)
- Verifica ca toate tabelele sunt lizibile pe mobile
- Verifica ca linkurile externe (apple.com, metered.ca, railway.app) functioneaza

---

## Sarcina 2 — Hosteaza pagina la un URL public

### Optiunea A: GitHub Pages (RECOMANDAT — cel mai simplu)

**Prerequisite:** Repo-ul QRChat trebuie sa fie pe GitHub.

```bash
cd /Users/ruslanconstantinovici/QRChat

# Verifica daca exista remote
git remote -v

# Daca repo-ul e pe GitHub:
# 1. Commit docs/privacy.html
git add docs/privacy.html
git commit -m "Add Privacy Policy HTML page for App Store"

# 2. Push
git push origin main

# 3. Activeaza GitHub Pages:
#    - Du-te la Settings > Pages in repo-ul GitHub
#    - Source: Deploy from branch
#    - Branch: main, folder: /docs
#    - Save
#
# SAU foloseste gh CLI:
gh api repos/{owner}/{repo}/pages -X POST -f source.branch=main -f source.path=/docs

# URL-ul va fi: https://{username}.github.io/{repo}/privacy.html
```

**ATENTIE:** GitHub Pages poate dura 1-2 minute sa se activeze prima data. Verifica cu:
```bash
curl -s -o /dev/null -w "%{http_code}" https://{username}.github.io/{repo}/privacy.html
```

### Optiunea B: Netlify (alternativa — drag & drop)

Daca GitHub Pages nu e disponibil:

1. Du-te la https://app.netlify.com/drop
2. Trage folderul `docs/` in browser
3. Netlify va genera un URL random (ex: `https://abc123.netlify.app/privacy.html`)
4. Optional: seteaza custom domain `qrchat.app` daca ai acces la DNS

### Optiunea C: Vercel

```bash
# Daca ai Vercel CLI instalat:
cd /Users/ruslanconstantinovici/QRChat/docs
npx vercel --prod
# Va genera un URL public
```

### Alegerea URL-ului final

Indiferent de optiunea aleasa, URL-ul final trebuie sa fie stabil (nu se schimba). Prioritatea:
1. `https://qrchat.app/privacy` — daca ai acces la domeniu si DNS
2. `https://{username}.github.io/QRChat/privacy.html` — GitHub Pages
3. `https://{site-id}.netlify.app/privacy.html` — Netlify

---

## Sarcina 3 — Actualizeaza URL-ul in toate locurile

Dupa ce ai URL-ul public functional, actualizeaza-l in:

### 1. Info.plist
```
Fisier: ios/QRChat/Info.plist
Linia 92: <string>https://qrchat.app/privacy</string>
→ inlocuieste cu URL-ul real
```

### 2. App Store Connect
Cand faci submission, in sectiunea "App Information" > "Privacy Policy URL" trebuie sa fie acelasi URL.

### 3. Comunica catre frontend-engineer
Trimite un mesaj in `agent-runtime/messages/` catre frontend-engineer cu URL-ul final, pentru ca el sa il foloseasca in SettingsScreen (vezi Prompt 5, Sarcina 4).

---

## Sarcina 4 — Verifica ca pagina este accesibila

```bash
# Testeaza URL-ul final
curl -s -o /dev/null -w "%{http_code}" <URL_FINAL>
# Trebuie sa raspunda 200

# Testeaza ca HTML-ul e valid
curl -s <URL_FINAL> | head -5
# Trebuie sa inceapa cu <!DOCTYPE html>

# Deschide in Safari (important — Apple Review va folosi Safari)
open -a Safari <URL_FINAL>
```

---

## Dupa finalizare

1. Noteaza URL-ul final in `agent-runtime/outputs/privacy-policy-url.md`
2. Trimite mesaj catre frontend-engineer cu URL-ul
3. Actualizeaza `agent-runtime/state/status.md`
