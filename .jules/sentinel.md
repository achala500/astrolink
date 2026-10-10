## 2026-10-10 - Hardcoded Private Ed25519 Key in Offline Licensing Module
**Vulnerability:** Master Ed25519 private key was hardcoded in `backend/app/licensing.py`, allowing client binaries and codebase inspection to mint valid unlimited licenses.
**Learning:** Offline asymmetric license verification requires only the master public key in client code; keeping fallback private keys in production modules breaks key segregation.
**Prevention:** Always require private signing keys via `ASTROLINK_MASTER_PRIVATE_KEY` environment variable or explicit CLI parameters, raising an error if missing.
