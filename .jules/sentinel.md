# Sentinel's Security Journal

## 2026-11-09 - Hardcoded Ed25519 Private Signing Key in Licensing Module
**Vulnerability:** A 32-byte Ed25519 master private signing key was hardcoded in `backend/app/licensing.py` (`_MASTER_PRIVATE_KEY_HEX`), exposing the signing authority directly in the codebase and packaged desktop binary releases. Anyone inspecting the code or reverse-engineering the binary could forge unlimited lifetime commercial licenses.
**Learning:** Offline cryptographic validation schemes require storing the master public key for verification, but private signing keys must never be shipped or committed alongside verification logic. The minting function should strictly fetch private keys from secure server environment variables (`ASTROLINK_MASTER_PRIVATE_KEY` / `ASTROLINK_PRIVATE_KEY`) or explicit arguments, never hardcoded fallbacks.
**Prevention:** Separate license minting and verification responsibilities. Ensure private keys are injected dynamically in CI/CD or licensing servers via environment variables, and enforce automated secret scanning to prevent private key definitions in application modules.
