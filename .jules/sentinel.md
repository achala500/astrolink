## 2025-05-18 - Hardcoded Asymmetric Private Signing Key
**Vulnerability:** A hardcoded master Ed25519 private key was embedded directly in `backend/app/licensing.py`, exposing offline license signing credentials in client-side / application source code.
**Learning:** Private signing keys used for generating licenses or cryptographically signed tokens should never reside in application source code, even if marked as optional or internal.
**Prevention:** Always inject private signing keys at runtime via environment variables (e.g., `ASTROLINK_MASTER_PRIVATE_KEY`) or explicit parameters, and fail explicitly if missing when executing signing operations.
