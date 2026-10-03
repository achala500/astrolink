"""Regression tests for the browser-free camera bridge."""

from pathlib import Path

from astrolink_camera_agent import wait_for_stable_file


def test_camera_agent_waits_for_complete_file(tmp_path: Path) -> None:
    """A non-empty completed exposure is accepted by the stability gate."""
    exposure = tmp_path / "capture.fits"
    exposure.write_bytes(b"complete exposure")
    assert wait_for_stable_file(exposure, checks=2, interval=0.01) is True


def test_camera_agent_rejects_missing_file(tmp_path: Path) -> None:
    """Missing camera files are never sent to the server."""
    assert wait_for_stable_file(tmp_path / "missing.fits", checks=1, interval=0.01) is False
