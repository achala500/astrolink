## 2026-03-31 - Hardcoded Private Key in License Module
**Vulnerability:** Hardcoded Ed25519 private key (`_MASTER_PRIVATE_KEY_HEX`) in `backend/app/licensing.py`.
**Learning:** Private signing keys embedded in client/open-source application source code allow anyone to forge valid licenses and bypass cryptographic limits.
**Prevention:** Private keys for minting/signing must never be embedded in application binaries or codebase; they must only be supplied via secure environment variables or external KMS during minting operations.
