## 2026-03-30 - Prevent Hardcoded Cryptographic Signing Keys
**Vulnerability:** Master Ed25519 private key was hardcoded in application code (`_MASTER_PRIVATE_KEY_HEX`), allowing anyone with source code or binary access to forge valid license keys.
**Learning:** Offline signing utilities must require private keys via environment variables or explicit parameters rather than fallback defaults in source files.
**Prevention:** Always require private keys via environment variables (e.g. `ASTROLINK_MASTER_PRIVATE_KEY`) or explicit arguments for minting/signing operations, raising an error if missing.
