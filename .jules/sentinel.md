# Sentinel Journal - Security Learnings

## 2026-11-06 - Hardcoded Asymmetric Cryptographic Signing Key in Binary Builds
**Vulnerability:** The Ed25519 private signing key (`_MASTER_PRIVATE_KEY_HEX`) was hardcoded as a module-level constant in `backend/app/licensing.py`. Anyone inspecting the source code or reversing PyInstaller binary releases could extract this master private key and mint arbitrary authentic offline licenses.
**Learning:** Development and CLI conveniences can easily result in private keys being checked in and bundled into distribution artifacts. Even if public key verification is properly decoupled, key generation tools sharing the same module can leak secret signing materials.
**Prevention:** Never define master private signing keys in client-facing application code or binary distribution modules. Require secret keys to be provided dynamically via environment variables (`ASTROLINK_MASTER_PRIVATE_KEY`) or dedicated offline server signing vaults, while unit tests inject isolated ephemeral keys via test fixtures.
