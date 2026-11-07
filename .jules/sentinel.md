# Sentinel's Security Journal

## 2026-11-07 - Remove Hardcoded Ed25519 Master Private Key from Licensing Module
**Vulnerability:** A 32-byte Ed25519 master private signing key (`_MASTER_PRIVATE_KEY_HEX`) was hardcoded in `backend/app/licensing.py`. Because AstroLink packages standalone desktop executables via PyInstaller, embedding the private key exposes it directly within compiled binaries and repository source code, allowing attackers or users to extract the key and forge unlimited lifetime licenses offline.
**Learning:** Asymmetric licensing schemes (e.g., Ed25519) rely on embedding solely the public verification key (`MASTER_PUBLIC_KEY_HEX`) in client distributions. Private signing keys must only exist on secure licensing infrastructure or be supplied via secure environment variables (`ASTROLINK_MASTER_PRIVATE_KEY` / `ASTROLINK_PRIVATE_KEY`) or explicit parameters during testing or key-minting CLI operations.
**Prevention:** Eliminate default/hardcoded private keys from client codebases. Enforce explicit key configuration (`private_key_hex` parameter or environment variables) in signing routines (`mint_license`), failing fast with a `ValueError` when unconfigured.
