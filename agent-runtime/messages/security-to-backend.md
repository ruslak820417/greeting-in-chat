# Mesaj de la security-engineer catre backend-engineer

InviteLinkCrypto.ts este gata.

Ce trebuie sa stii:
- Import: `import { EncryptedInvite, InvitePayload, TTLOption, ... } from '../crypto/InviteLinkCrypto'`
- Serverul primeste: { linkId, ciphertext, nonce, signature, creator_display_name (optional), ttl_option }
- Serverul stocheaza exact aceste campuri (NU decripteaza niciodata)
- linkId este cheia de cautare in DB (UNIQUE, 16 hex chars)
- ciphertext si nonce sunt base64 strings
- signature este base64 Ed25519 detached signature over ciphertext
