## 2026-10-25 - Hardcoded License Minting Private Key Removal

**Vulnerability:** A 32-byte Ed25519 private key (`_MASTER_PRIVATE_KEY_HEX`) was hardcoded in `backend/app/licensing.py` for minting offline license keys, exposing signing capability to anyone with access to the source code or binary.

**Learning:** Offline asymmetric license verification requires only the public key in the client binary. The signing private key must never be shipped or hardcoded in application code.

**Prevention:** Load private keys for signing/minting functions solely from environment variables (`ASTROLINK_MASTER_PRIVATE_KEY` / `ASTROLINK_PRIVATE_KEY`) or explicit function parameters, raising an explicit error if missing.
