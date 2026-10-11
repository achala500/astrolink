# Sentinel Security Journal

## 2026-03-30 - Hardcoded Private Key in Licensing Module
**Vulnerability:** The offline licensing module contained a hardcoded Ed25519 master private key (`_MASTER_PRIVATE_KEY_HEX`) in application source code, allowing anyone with access to the source code or binary to mint arbitrary valid licenses.
**Learning:** Private signing keys were embedded directly in source code for convenience during testing and offline key minting CLI usage.
**Prevention:** Always require private keys to be supplied via secure environment variables (`ASTROLINK_MASTER_PRIVATE_KEY`) or explicit function parameters, and ensure source code only contains public verification keys.
