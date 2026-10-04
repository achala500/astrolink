"""Tests for feedback attachment path traversal security."""

import pytest
from pathlib import Path
from backend.app.feedback import FeedbackManager


def test_get_attachment_path_valid(tmp_path):
    """Should return resolved target path when file exists inside attachments directory."""
    fb_file = tmp_path / "feedback.json"
    mgr = FeedbackManager(feedback_file=fb_file)

    test_file = mgr.attachments_dir / "valid_image.png"
    test_file.write_text("dummy image data")

    res = mgr.get_attachment_path("valid_image.png")
    assert res is not None
    assert res.resolve() == test_file.resolve()


def test_get_attachment_path_traversal_attempts(tmp_path):
    """Path traversal attempts should return None and not leak outside attachments directory."""
    fb_file = tmp_path / "feedback.json"
    mgr = FeedbackManager(feedback_file=fb_file)

    # Create a sensitive file outside attachments dir
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("super_secret_data")

    # Try various path traversal vectors
    traversal_payloads = [
        "../secret.txt",
        "../../secret.txt",
        "..%2fsecret.txt",
        "/etc/passwd",
        "feedback.json",
        "../feedback.json",
        "",
    ]

    for payload in traversal_payloads:
        res = mgr.get_attachment_path(payload)
        assert res is None, f"Expected None for payload '{payload}', but got {res}"
