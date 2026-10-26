## 2026-10-23 - Hardcoded Master Private Signing Key Removal
**Vulnerability:** A hardcoded master Ed25519 private signing key (`_MASTER_PRIVATE_KEY_HEX`) in `backend/app/licensing.py` allowed anyone with source or binary access to mint valid license keys.
**Learning:** License minting code shipped inside application binaries or repositories must never retain private signing keys.
**Prevention:** Require `ASTROLINK_MASTER_PRIVATE_KEY` environment variable or explicit function arguments when minting licenses, and keep private signing keys restricted to secure deployment pipelines.
