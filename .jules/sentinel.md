## 2026-03-30 - Remove Hardcoded Private Signing Key
**Vulnerability:** A 32-byte Ed25519 private signing key (`_MASTER_PRIVATE_KEY_HEX`) was hardcoded in `backend/app/licensing.py`.
**Learning:** Hardcoding private signing keys in client or server application code allows anyone with access to the source or compiled binary to extract the secret key and generate arbitrary valid licenses.
**Prevention:** Always isolate cryptographic signing private keys in external environment variables (e.g., `ASTROLINK_MASTER_PRIVATE_KEY`) or dedicated key management services. Application code must fail securely if the private key is missing rather than falling back to an in-code default.
