# PROMPT 1 — Android Release Build

**Agent tinta:** release-engineer
**Proiect:** `/Users/ruslanconstantinovici/qrchatAndroid`
**Obiectiv:** Genereaza signing keystore, configureaza Gradle signing, fa AAB release build functional

---

## Context

Copia Android a QRChat se afla la `/Users/ruslanconstantinovici/qrchatAndroid`. Build-ul curent de release foloseste keystore-ul de DEBUG (linia 103 din `build.gradle`):

```groovy
release {
    signingConfig signingConfigs.debug  // <-- PROBLEMA: debug keystore pentru release
}
```

Configuratia curenta:
- **applicationId:** `com.qrchat`
- **versionCode:** 1, **versionName:** "1.0"
- **Hermes:** enabled (`hermesEnabled=true` in `gradle.properties`)
- **New Architecture:** enabled (`newArchEnabled=true`)
- **ProGuard:** disabled (`enableProguardInReleaseBuilds = false`)
- **Architectures:** armeabi-v7a, arm64-v8a, x86, x86_64

Nu exista inca un `keystore.properties` sau un keystore de productie.

---

## Sarcini — pas cu pas

### Pas 1 — Genereaza keystore de productie

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid/android/app

keytool -genkeypair \
  -v \
  -storetype PKCS12 \
  -keystore qrchat-release.keystore \
  -alias qrchat-key \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -dname "CN=QRChat, OU=Mobile, O=QRChat, L=Chisinau, ST=Chisinau, C=MD"
```

- Foloseste o parola puternica (minim 12 caractere)
- Noteaza parola — o vei pune in `keystore.properties`
- Keystore-ul va fi la: `android/app/qrchat-release.keystore`

**IMPORTANT:** NU adauga keystore-ul in git! Verifica ca `.gitignore` contine `*.keystore`.

### Pas 2 — Creaza `keystore.properties`

Creaza fisierul `/Users/ruslanconstantinovici/qrchatAndroid/android/keystore.properties`:

```properties
storeFile=qrchat-release.keystore
storePassword=PAROLA_TA_AICI
keyAlias=qrchat-key
keyPassword=PAROLA_TA_AICI
```

**IMPORTANT:** NU adauga `keystore.properties` in git! Adauga-l in `.gitignore`.

### Pas 3 — Configureaza `signingConfigs` in build.gradle

Editeaza `/Users/ruslanconstantinovici/qrchatAndroid/android/app/build.gradle`:

```groovy
// La inceputul blocului android {}, inainte de signingConfigs:
def keystorePropertiesFile = rootProject.file("keystore.properties")
def keystoreProperties = new Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    // ... (ndkVersion, buildToolsVersion, compileSdk raman la fel)

    signingConfigs {
        debug {
            storeFile file('debug.keystore')
            storePassword 'android'
            keyAlias 'androiddebugkey'
            keyPassword 'android'
        }
        release {
            if (keystorePropertiesFile.exists()) {
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
            }
        }
    }
    buildTypes {
        debug {
            signingConfig signingConfigs.debug
        }
        release {
            signingConfig signingConfigs.release  // <-- SCHIMBAT de la debug
            minifyEnabled enableProguardInReleaseBuilds
            proguardFiles getDefaultProguardFile("proguard-android.txt"), "proguard-rules.pro"
        }
    }
}
```

### Pas 4 — Actualizeaza `.gitignore`

Verifica/adauga in `/Users/ruslanconstantinovici/qrchatAndroid/android/.gitignore`:

```
keystore.properties
*.keystore
!debug.keystore
```

### Pas 5 — Build AAB (Android App Bundle)

```bash
cd /Users/ruslanconstantinovici/qrchatAndroid/android

# Clean build anterior
./gradlew clean

# Build AAB pentru Google Play
./gradlew bundleRelease
```

**Output asteptat:** `android/app/build/outputs/bundle/release/app-release.aab`

Daca vrei si APK (pentru testare directa pe dispozitiv):
```bash
./gradlew assembleRelease
```
**Output APK:** `android/app/build/outputs/apk/release/app-release.apk`

### Pas 6 — Verifica AAB-ul

```bash
# Verifica semnatura
jarsigner -verify -verbose -certs android/app/build/outputs/bundle/release/app-release.aab

# Verifica dimensiunea
ls -lh android/app/build/outputs/bundle/release/app-release.aab

# (Optional) Testeaza cu bundletool — genereaza APK-uri din AAB
# Descarca bundletool: https://github.com/google/bundletool/releases
# java -jar bundletool.jar build-apks \
#   --bundle=app-release.aab \
#   --output=app-release.apks \
#   --ks=app/qrchat-release.keystore \
#   --ks-key-alias=qrchat-key
```

### Pas 7 — Testeaza APK-ul pe emulator

```bash
# Porneste emulatorul
~/Library/Android/sdk/emulator/emulator -avd Medium_Phone_API_36.1 &

# Asteapta sa booteze
~/Library/Android/sdk/platform-tools/adb wait-for-device

# Instaleaza APK-ul
~/Library/Android/sdk/platform-tools/adb install android/app/build/outputs/apk/release/app-release.apk

# Verifica ca se deschide
~/Library/Android/sdk/platform-tools/adb shell am start -n com.qrchat/.MainActivity
```

---

## Fisiere de modificat

| Fisier | Actiune |
|--------|---------|
| `android/app/build.gradle` | Adauga release signingConfig (Pas 3) |
| `android/keystore.properties` | Creaza NOU (Pas 2) |
| `android/app/qrchat-release.keystore` | Genereaza NOU (Pas 1) |
| `android/.gitignore` | Adauga keystore.properties + *.keystore (Pas 4) |

---

## Criterii de succes

1. `./gradlew bundleRelease` se termina fara erori
2. Fisierul `app-release.aab` exista si are >5MB
3. `jarsigner -verify` confirma semnatura valida (NU debug keystore)
4. APK-ul se instaleaza pe emulator si aplicatia porneste
5. `keystore.properties` si `*.keystore` sunt in `.gitignore`

---

## Capcane de evitat

- **NU folosi debug keystore pentru release** — Google Play va REFUZA upload-ul daca detecteaza debug certificate
- **NU adauga keystore-ul sau parolele in git** — risc de securitate major
- **NU activa ProGuard** deocamdata (`enableProguardInReleaseBuilds = false`) — poate strica Hermes bytecode sau native module React Native daca nu e configurat corect cu reguli proguard
- **NU modifica `versionCode`/`versionName`** fara aprobare — ramane 1/"1.0" pana cand qa-engineer confirma build-ul
- **Diferenta AAB vs APK:** Google Play CERE AAB (nu APK) incepand din 2021. Foloseste `bundleRelease` pentru Play Store, `assembleRelease` doar pentru testare locala
- **Hermes bytecode:** Cu Hermes enabled, JS-ul este compilat in bytecode la build time. Daca build-ul esueaza cu erori Hermes, verifica ca `hermesEnabled=true` in `gradle.properties` si ca nu ai erori de sintaxa JS
- **Architecture filtering:** Pentru build final Play Store, poti reduce dimensiunea excludand x86/x86_64 (doar emulatoare) din `reactNativeArchitectures` in `gradle.properties`. Dar NU face asta pana dupa testare pe emulator!
