# PROMPT 8 — Language + Theme Selectors on SetupScreen

**Agent:** frontend-engineer
**Proiect:** `/Users/ruslanconstantinovici/QRChat`
**Fisiere de citit INAINTE de a incepe:**
- `src/screens/SetupScreen.tsx` (ecranul de modificat)
- `src/screens/SettingsScreen.tsx` (liniile 220-330 — referinta pentru selectoare existente)
- `src/i18n/index.ts` (LANGUAGES array, changeLanguage function, LanguageCode type)
- `src/utils/ThemeContext.tsx` (THEME_LIST, ThemeId, useTheme hook cu setThemeId)

---

## Obiectiv

Pe SetupScreen (ecranul de onboarding unde utilizatorul isi pune numele la prima pornire), adauga **INAINTE** de input-ul cu numele:
1. **Selector de limba** (EN/RO/RU/FR)
2. **Selector de tema** (Light/Dark)

Ambele selectii se aplica IMEDIAT — limba schimba interfata pe loc, tema schimba culorile instantaneu.

---

## Context design — cum fac altii

### WhatsApp
- La prima lansare, WhatsApp afiseaza limba ca **primul ecran** — o lista plata cu toate limbile, font mare, centrat
- Utilizatorul selecteaza limba INAINTE de a vedea orice alt ecran
- Nu are selector de tema in onboarding

### Telegram
- Telegram detecteaza limba device-ului automat, dar ofera optiune de schimbare rapida in onboarding
- Design minimalist — pill buttons sau lista scurta
- Recent (2025-2026) Telegram a adoptat design "Liquid Glass" pe iOS — efecte translucide, animatii smooth

### Signal
- Signal ofera selector de limba la prima pornire, similar cu WhatsApp
- Design simplu, functional, fara ornamente

### Abordarea noastra (QRChat)
- NU facem ecran separat pentru limba — totul ramane pe un singur ecran compact
- Selectoarele sunt deasupra input-ului de nume, compacte si elegante
- Limba se aplica imediat (changeLanguage rerandeaza toate t() keys)
- Tema se aplica imediat (setThemeId schimba culorile)

---

## Specificatii tehnice detaliate

### 1. Selector de limba — pill buttons

**Pozitionare:** Imediat sub iconita person-outline, INAINTE de titlu si input

**Layout:**
```
[EN] [RO] [RU] [FR]    ← butoane pill orizontale, centrate
```

**Design:**
- `flexDirection: 'row'`, `justifyContent: 'center'`, `gap: 8`, `marginBottom: 20`
- Fiecare pill: `paddingHorizontal: 16`, `paddingVertical: 8`, `borderRadius: 20`
- Pill ACTIV: `backgroundColor: C.primary`, text `color: '#fff'`, `fontWeight: '600'`
- Pill INACTIV: `backgroundColor: C.surface`, text `color: C.textSecondary`, `borderWidth: 1`, `borderColor: C.border`
- Animatie subtila la selectie (opacity 0.8 pe press)
- Font size: 14

**Implementare:**
```tsx
import { LANGUAGES, changeLanguage } from '../i18n';
import type { LanguageCode } from '../i18n';
// In componenta:
const { t, i18n } = useTranslation();

// Render:
<View style={styles.languageRow}>
  {LANGUAGES.map(lang => {
    const isActive = i18n.language === lang.code;
    return (
      <TouchableOpacity
        key={lang.code}
        style={[
          styles.langPill,
          { backgroundColor: isActive ? C.primary : C.surface,
            borderColor: isActive ? C.primary : C.border,
            borderWidth: 1 },
        ]}
        onPress={() => changeLanguage(lang.code as LanguageCode)}
        activeOpacity={0.7}
        accessibilityLabel={`Language: ${lang.label}`}
        accessibilityRole="radio"
        accessibilityState={{ selected: isActive }}
      >
        <Text style={{
          color: isActive ? '#fff' : C.textSecondary,
          fontSize: 14,
          fontWeight: isActive ? '600' : '400',
        }}>
          {lang.code.toUpperCase()}
        </Text>
      </TouchableOpacity>
    );
  })}
</View>
```

**Label deasupra (optional dar recomandat):**
- Un mic text "Language" / label static deasupra pill-urilor
- NU folosi t() pentru acest label — trebuie sa fie vizibil inainte de selectia limbii
- Poti folosi un icon `globe-outline` de 16px + text mic "Language" in gri (`C.textMuted`, fontSize 12)

### 2. Selector de tema — 2 mini-carduri

**Pozitionare:** Sub selectorul de limba, INAINTE de titlu

**Layout:**
```
[ ☀ Light ]  [ 🌙 Dark ]    ← 2 carduri compacte, centrate
```

**Design:**
- `flexDirection: 'row'`, `justifyContent: 'center'`, `gap: 12`, `marginBottom: 24`
- Fiecare card: `width: 100`, `paddingVertical: 10`, `borderRadius: 12`, `alignItems: 'center'`
- Card ACTIV: `borderWidth: 2`, `borderColor: C.primary`, `backgroundColor: C.surface`
- Card INACTIV: `borderWidth: 1`, `borderColor: C.border`, `backgroundColor: C.surface`
- Icon Ionicons: `sunny-outline` pentru Light, `moon-outline` pentru Dark (size 20)
- Text sub icon: `fontSize: 12`, `marginTop: 4`

**Implementare:**
```tsx
import { THEME_LIST, ThemeId } from '../utils/ThemeContext';
// In componenta:
const { theme: C, themeId, setThemeId } = useTheme();

// Render:
<View style={styles.themeRow}>
  {THEME_LIST.map(th => {
    const isActive = themeId === th.id;
    return (
      <TouchableOpacity
        key={th.id}
        style={[
          styles.themeOption,
          { backgroundColor: C.surface,
            borderColor: isActive ? C.primary : C.border,
            borderWidth: isActive ? 2 : 1 },
        ]}
        onPress={() => setThemeId(th.id as ThemeId)}
        activeOpacity={0.7}
        accessibilityLabel={`Theme: ${th.name}${isActive ? ', active' : ''}`}
        accessibilityRole="radio"
        accessibilityState={{ selected: isActive }}
      >
        <Ionicons
          name={th.id === 'dark' ? 'moon-outline' : 'sunny-outline'}
          size={20}
          color={isActive ? C.primary : C.textSecondary}
        />
        <Text style={{
          fontSize: 12,
          marginTop: 4,
          color: isActive ? C.primary : C.textSecondary,
          fontWeight: isActive ? '600' : '400',
        }}>
          {th.name}
        </Text>
      </TouchableOpacity>
    );
  })}
</View>
```

### 3. Ordinea elementelor in step === 'name'

```
<iconContainer>          ← person-outline (existent)
<languageRow>            ← NOU — pill buttons EN/RO/RU/FR
<themeRow>               ← NOU — Light / Dark mini-carduri
<title>                  ← "Welcome" / t('setup.title') (existent)
<subtitle>               ← t('setup.subtitle') (existent)
<input>                  ← TextInput nume (existent)
<checkbox terms>         ← agreedToTerms (existent)
<button generate>        ← buton principal (existent)
<info text>              ← shield info (existent)
```

### 4. Stiluri noi de adaugat in StyleSheet

```tsx
languageRow: {
  flexDirection: 'row',
  justifyContent: 'center',
  gap: 8,
  marginBottom: 16,
},
langPill: {
  paddingHorizontal: 16,
  paddingVertical: 8,
  borderRadius: 20,
},
themeRow: {
  flexDirection: 'row',
  justifyContent: 'center',
  gap: 12,
  marginBottom: 24,
},
themeOption: {
  width: 100,
  paddingVertical: 10,
  borderRadius: 12,
  alignItems: 'center',
},
```

---

## Reguli stricte

1. **NU scoate** selectoarele din SettingsScreen — ele raman si acolo
2. **NU modifica** step-urile 'generating' si 'done' — doar step 'name'
3. **NU adauga** dependinte noi (npm packages) — foloseste doar ce exista deja
4. **Selectiile se aplica IMEDIAT** — changeLanguage() si setThemeId() schimba UI-ul pe loc
5. Pastreaza `autoFocus` pe TextInput — selectoarele sunt deasupra, utilizatorul scrolleaza natural
6. Testeaza pe AMBELE teme (light + dark) — selectoarele trebuie sa arate bine pe ambele
7. Accessibility labels pe toate elementele interactive (accessibilityRole="radio", accessibilityState)
8. Dupa modificare, deploy pe simulator SI telefon fizic

---

## Verificare finala

- [ ] Pill-urile de limba arata corect si schimba limba instant
- [ ] Cardurile de tema arata corect si schimba tema instant
- [ ] Titlul si subtitlul se actualizeaza cand se schimba limba
- [ ] Selectiile persista (la restart, limba si tema sunt cele alese)
- [ ] SetupScreen arata bine pe iPhone SE (ecran mic) — elementele nu se suprapun
- [ ] SettingsScreen inca are selectoarele sale intacte
- [ ] Testat pe simulator + telefon fizic
