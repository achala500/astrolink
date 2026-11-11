# Sentinel Security Journal

## 2026-11-11 - Hardcoded Asymmetric Private Signing Key in Client-Distributed Modules
**Vulnerability:** The Ed25519 master private key (`_MASTER_PRIVATE_KEY_HEX`) was hardcoded directly in `backend/app/licensing.py`. In an application bundled as a standalone desktop binary via PyInstaller or distributed as container images, hardcoded private keys can be extracted through binary inspection or reverse engineering, allowing arbitrary minting and bypassing offline license enforcement.
**Learning:** Utilities for generating or minting signed artifacts often inadvertently share modules with client-side verification logic. When packaging client applications, minting code should never bundle embedded private signing keys.
**Prevention:** Strictly enforce retrieval of asymmetric signing keys from secure environment variables (`ASTROLINK_MASTER_PRIVATE_KEY` / `ASTROLINK_PRIVATE_KEY`) or dedicated server-side tooling, raising an immediate error if absent, ensuring only public verification keys reside in client-distributed binaries.
