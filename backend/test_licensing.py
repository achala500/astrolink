"""Tests for AstroLink offline cryptographic licensing and frame limits."""

import base64
import json
import numpy as np
import pytest

from backend.app.licensing import (
    LicenseManager,
    UNVERIFIED_FRAME_LIMIT,
    mint_license,
    verify_license_key,
)
from backend.app.main import AstrophotographySession

TEST_PRIVATE_KEY = "c0da84c7fc6f83c8acc46e4b95150f60c267e4f1e0ceffcdf460be0ed9f2c0fd"


@pytest.fixture(autouse=True)
def setup_test_master_key(monkeypatch):
    """Automatically provides the master test signing key in environment for licensing tests."""
    monkeypatch.setenv("ASTROLINK_MASTER_PRIVATE_KEY", TEST_PRIVATE_KEY)


def test_mint_without_private_key_raises_error(monkeypatch):
    """Minting a license without an environment key or explicit argument must raise ValueError."""
    monkeypatch.delenv("ASTROLINK_MASTER_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ASTROLINK_PRIVATE_KEY", raising=False)
    with pytest.raises(ValueError, match="Private key is required to mint licenses"):
        mint_license("Unauthorized", "lifetime")


def test_mint_and_verify_valid_license():
    """Valid Ed25519 license should verify completely offline with unlimited frames."""
    key = mint_license("Hubble Observer", "lifetime")
    assert isinstance(key, str)
    assert len(key) > 50

    status = verify_license_key(key)
    assert status.is_valid is True
    assert status.licensee == "Hubble Observer"
    assert status.tier == "lifetime"
    assert status.max_frames is None  # Unlimited
    assert status.error is None


def test_tampered_license_rejection():
    """Tampering with licensee or tier must fail cryptographic verification."""
    valid_key = mint_license("Carl Sagan", "lifetime")
    payload = json.loads(base64.b64decode(valid_key).decode("utf-8"))

    # Tamper with the licensee name
    payload["licensee"] = "Imposter"
    tampered_bytes = json.dumps(payload).encode("utf-8")
    tampered_key = base64.b64encode(tampered_bytes).decode("ascii")

    status = verify_license_key(tampered_key)
    assert status.is_valid is False
    assert status.max_frames == UNVERIFIED_FRAME_LIMIT
    assert "Cryptographic signature mismatch" in (status.error or "")


def test_malformed_key_handling():
    """Corrupted base64 or invalid JSON must fail gracefully without crashing."""
    status = verify_license_key("not-a-valid-base64-string!@#$")
    assert status.is_valid is False
    assert status.max_frames == UNVERIFIED_FRAME_LIMIT
    assert status.error is not None

    empty_status = verify_license_key("")
    assert empty_status.is_valid is False
    assert empty_status.max_frames == UNVERIFIED_FRAME_LIMIT


def test_license_manager_activation_and_deactivation(tmp_path):
    """LicenseManager should handle activation, in-memory status, and deactivation."""
    key_file = tmp_path / "test_license.key"
    mgr = LicenseManager(key_path=key_file)

    # Initial state: unverified trial
    assert mgr.is_licensed() is False
    assert mgr.get_max_frames() == 10

    # Activate valid key
    valid_key = mint_license("Galileo Galilei", "field_pro")
    status = mgr.activate_license(valid_key, persist=True)
    assert status.is_valid is True
    assert mgr.is_licensed() is True
    assert mgr.get_max_frames() is None
    assert key_file.is_file()

    # Deactivate
    mgr.deactivate()
    assert mgr.is_licensed() is False
    assert mgr.get_max_frames() == 10
    assert not key_file.is_file()


def test_stacking_frame_limit_enforcement():
    """Unverified instances must be capped at 10 frames maximum."""
    sess = AstrophotographySession()
    sess.reset()

    # Create dummy aligned star frame
    h, w = 300, 300
    frame = np.full((h, w, 3), 0.05, dtype=np.float32)
    # Add star
    frame[150, 150] = 0.95

    # Simulate stacker having reached 10 frames
    sess.stacker.total_frames_processed = 10

    # Next frame should be rejected due to trial limit
    res = sess.process_frame(frame, "frame_011.fits", sub_exp_seconds=5.0)
    assert res["accepted"] is False
    assert res["reason"] == "license_limit_reached"
    assert "TRIAL_LIMIT" in res["details"]
