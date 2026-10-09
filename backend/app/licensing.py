"""Offline Cryptographic License Validator for AstroLink.

Implements 100% offline asymmetric Ed25519 signature verification.
Zero external network pings. If unverified, the stacking engine is
limited to a maximum of 10 frames per session.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger("astrolink.licensing")

# Master hardcoded 32-byte Ed25519 public key (hex-encoded)
# Used exclusively for in-binary offline verification
MASTER_PUBLIC_KEY_HEX: str = "1658de0da16562b43a7afbf9fa6e84589ce1c28b260259640dbb17001a4b7dd0"

# Community Trial frame limit for unverified instances
UNVERIFIED_FRAME_LIMIT: int = 10


@dataclass(frozen=True)
class LicenseStatus:
    """Immutable representation of license verification state."""

    is_valid: bool
    licensee: str
    tier: str  # "lifetime", "field_pro", "community_trial", etc.
    max_frames: Optional[int]  # None = Unlimited; int = session limit
    signature: Optional[str] = None
    issued_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes license status for API responses."""
        return {
            "isValid": self.is_valid,
            "licensee": self.licensee,
            "tier": self.tier,
            "maxFrames": self.max_frames,
            "isUnlimited": self.max_frames is None,
            "error": self.error,
        }


def _get_public_key() -> ed25519.Ed25519PublicKey:
    """Loads the hardcoded public key from bytes."""
    pub_bytes = bytes.fromhex(MASTER_PUBLIC_KEY_HEX)
    return ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)


def _decode_signature(sig_str: str) -> bytes:
    """Decodes signature from either standard base64 or hex format."""
    sig_str = sig_str.strip()
    # Try base64 decoding first
    try:
        raw_b64 = base64.b64decode(sig_str)
        if len(raw_b64) == 64:
            return raw_b64
    except (ValueError, binascii.Error):
        pass

    # Try hex decoding
    try:
        raw_hex = bytes.fromhex(sig_str)
        if len(raw_hex) == 64:
            return raw_hex
    except ValueError:
        pass

    # Fallback to standard base64 with padding fix
    padded = sig_str + "=" * ((4 - len(sig_str) % 4) % 4)
    return base64.b64decode(padded)


def verify_license_key(license_key_str: str) -> LicenseStatus:
    """Performs 100% offline asymmetric verification of an AstroLink license key.

    The license key string is a base64 payload containing:
    `{"licensee": "Name", "tier": "lifetime", "signature": "..."}`.

    Args:
        license_key_str: Raw base64 encoded license key string.

    Returns:
        LicenseStatus detailing validity, licensee, tier, and frame limit.
    """
    if not license_key_str or not license_key_str.strip():
        return LicenseStatus(
            is_valid=False,
            licensee="Unregistered Field User",
            tier="community_trial",
            max_frames=UNVERIFIED_FRAME_LIMIT,
            error="No license key provided",
        )

    clean_str = license_key_str.strip()
    try:
        # 1. Base64 decode the outer container
        # Handle possible padding variations
        padded_str = clean_str + "=" * ((4 - len(clean_str) % 4) % 4)
        decoded_bytes = base64.b64decode(padded_str)
        payload = json.loads(decoded_bytes.decode("utf-8"))
    except Exception as e:
        logger.warning("License decode error: %s", e)
        return LicenseStatus(
            is_valid=False,
            licensee="Unregistered Field User",
            tier="community_trial",
            max_frames=UNVERIFIED_FRAME_LIMIT,
            error=f"Malformed license container: {e}",
        )

    # 2. Extract payload fields
    licensee = payload.get("licensee")
    tier = payload.get("tier", "standard")
    sig_str = payload.get("signature")
    issued_at = payload.get("issued_at")

    if not licensee or not sig_str:
        return LicenseStatus(
            is_valid=False,
            licensee=licensee or "Unregistered Field User",
            tier="community_trial",
            max_frames=UNVERIFIED_FRAME_LIMIT,
            error="Missing licensee or signature field in payload",
        )

    # 3. Decode signature bytes (64 bytes for Ed25519)
    try:
        sig_bytes = _decode_signature(sig_str)
        if len(sig_bytes) != 64:
            raise ValueError(f"Invalid Ed25519 signature length ({len(sig_bytes)} != 64)")
    except Exception as e:
        return LicenseStatus(
            is_valid=False,
            licensee=str(licensee),
            tier="community_trial",
            max_frames=UNVERIFIED_FRAME_LIMIT,
            error=f"Invalid signature encoding: {e}",
        )

    # 4. Canonical message reconstruction
    # Supports primary format: `f"{licensee}:{tier}".encode('utf-8')`
    # and structured JSON fallback: `json.dumps({"licensee": licensee, "tier": tier}, sort_keys=True)`
    candidate_messages = [
        f"{licensee}:{tier}".encode("utf-8"),
        json.dumps({"licensee": licensee, "tier": tier}, sort_keys=True).encode("utf-8"),
        f"{licensee}".encode("utf-8"),
    ]
    if issued_at:
        candidate_messages.append(f"{licensee}:{tier}:{issued_at}".encode("utf-8"))

    public_key = _get_public_key()
    verified = False

    for msg in candidate_messages:
        try:
            public_key.verify(sig_bytes, msg)
            verified = True
            break
        except InvalidSignature:
            continue

    if not verified:
        logger.warning("Ed25519 signature verification failed for licensee '%s'", licensee)
        return LicenseStatus(
            is_valid=False,
            licensee=str(licensee),
            tier="community_trial",
            max_frames=UNVERIFIED_FRAME_LIMIT,
            error="Cryptographic signature mismatch (unauthorized or tampered license)",
        )

    # 5. Successfully verified license!
    # Lifetime, pro, or verified licenses receive unlimited frame stacking.
    logger.info("AstroLink license verified offline for '%s' [Tier: %s]", licensee, tier)
    return LicenseStatus(
        is_valid=True,
        licensee=str(licensee),
        tier=str(tier),
        max_frames=None,  # Unlimited
        signature=sig_str,
        issued_at=issued_at,
        error=None,
    )


def mint_license(
    licensee: str,
    tier: str = "lifetime",
    issued_at: Optional[str] = None,
    private_key_hex: Optional[str] = None,
) -> str:
    """Mints a cryptographically signed AstroLink license key using Ed25519.

    Args:
        licensee: Full name or callsign of the astronomer.
        tier: License tier ("lifetime", "field_pro", etc.).
        issued_at: Optional ISO timestamp.
        private_key_hex: 32-byte Ed25519 private key in hex. Reads ASTROLINK_PRIVATE_KEY env var if None.

    Returns:
        Base64-encoded license key string ready for offline deployment.
    """
    priv_hex = private_key_hex or os.environ.get("ASTROLINK_PRIVATE_KEY")
    if not priv_hex:
        raise ValueError(
            "Private signing key required to mint license. "
            "Pass private_key_hex or set ASTROLINK_PRIVATE_KEY environment variable."
        )
    priv_bytes = bytes.fromhex(priv_hex)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)

    # Canonical message format
    if issued_at:
        message = f"{licensee}:{tier}:{issued_at}".encode("utf-8")
    else:
        message = f"{licensee}:{tier}".encode("utf-8")

    signature = private_key.sign(message)
    sig_b64 = base64.b64encode(signature).decode("ascii")

    payload: Dict[str, Any] = {
        "licensee": licensee,
        "tier": tier,
        "signature": sig_b64,
    }
    if issued_at:
        payload["issued_at"] = issued_at

    payload_json = json.dumps(payload, separators=(",", ":"))
    return base64.b64encode(payload_json.encode("utf-8")).decode("ascii")


class LicenseManager:
    """Manages offline license state, persistent storage, and stacking limits."""

    def __init__(self, key_path: Optional[Path] = None):
        self._key_path = key_path or self._resolve_default_key_path()
        self._current_status: LicenseStatus = self._load_initial_license()

    def _resolve_default_key_path(self) -> Path:
        """Determines default local storage path for license file."""
        # 1. Check local working directory
        cwd_key = Path("license.key")
        if cwd_key.is_file():
            return cwd_key

        # 2. Check user home config directory (~/.astrolink/license.key)
        home_dir = Path.home() / ".astrolink"
        return home_dir / "license.key"

    def _load_initial_license(self) -> LicenseStatus:
        """Loads and verifies license from environment variable or local file."""
        # 1. Environment variable override
        env_key = os.environ.get("ASTROLINK_LICENSE") or os.environ.get("ASTROLINK_LICENSE_KEY")
        if env_key:
            logger.info("Found ASTROLINK_LICENSE environment variable")
            return verify_license_key(env_key)

        # 2. Local file
        if self._key_path.is_file():
            try:
                file_content = self._key_path.read_text(encoding="utf-8").strip()
                if file_content:
                    logger.info("Found license file at %s", self._key_path)
                    return verify_license_key(file_content)
            except Exception as e:
                logger.warning("Failed to read license file %s: %s", self._key_path, e)

        # 3. Default to community trial
        return LicenseStatus(
            is_valid=False,
            licensee="Unregistered Field User",
            tier="community_trial",
            max_frames=UNVERIFIED_FRAME_LIMIT,
            error="No license key configured (Community Trial: 10 frames max)",
        )

    @property
    def status(self) -> LicenseStatus:
        """Returns the current active license status."""
        return self._current_status

    def is_licensed(self) -> bool:
        """Returns True if a valid cryptographic license is active."""
        return self._current_status.is_valid

    def get_max_frames(self) -> Optional[int]:
        """Returns max frames allowed per session (None = Unlimited, 10 = Trial)."""
        return self._current_status.max_frames

    def activate_license(self, license_key_str: str, persist: bool = True) -> LicenseStatus:
        """Verifies and activates a new license key in-memory and optionally on disk.

        Args:
            license_key_str: Base64-encoded license key string.
            persist: If True, writes the key to local disk.

        Returns:
            The verified LicenseStatus.
        """
        new_status = verify_license_key(license_key_str)
        self._current_status = new_status

        if new_status.is_valid and persist:
            try:
                self._key_path.parent.mkdir(parents=True, exist_ok=True)
                self._key_path.write_text(license_key_str.strip(), encoding="utf-8")
                logger.info("Successfully persisted license to %s", self._key_path)
            except Exception as e:
                logger.warning("Could not persist license to disk: %s", e)

        return new_status

    def deactivate(self) -> None:
        """Resets instance to community trial mode."""
        if self._key_path.is_file():
            self._key_path.unlink(missing_ok=True)
        self._current_status = LicenseStatus(
            is_valid=False,
            licensee="Unregistered Field User",
            tier="community_trial",
            max_frames=UNVERIFIED_FRAME_LIMIT,
            error="License deactivated",
        )


# Global singleton instance
license_manager = LicenseManager()


if __name__ == "__main__":
    # CLI helper for minting and verifying keys
    if len(sys.argv) > 1 and sys.argv[1] == "mint":
        name = sys.argv[2] if len(sys.argv) > 2 else "Dark Sky Explorer"
        tier_arg = sys.argv[3] if len(sys.argv) > 3 else "lifetime"
        minted_key = mint_license(name, tier_arg)
        print("\n================ AstroLink Master Key Minter ================")
        print(f"Licensee: {name}")
        print(f"Tier:     {tier_arg}")
        print(f"Key:      {minted_key}")
        print("=============================================================\n")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        key_to_verify = sys.argv[2] if len(sys.argv) > 2 else ""
        res = verify_license_key(key_to_verify)
        print(json.dumps(res.to_dict(), indent=2))
        sys.exit(0)

    print("Usage: python -m backend.app.licensing [mint <name> <tier> | verify <key>]")
