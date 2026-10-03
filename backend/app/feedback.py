"""Feedback collection system for AstroLink with Jules Autonomous Triage & Tracking.

Stores user-submitted feedback (bugs, suggestions, performance issues) in a local JSON file.
A scheduled GitHub Action reads this data, dedupes against existing GitHub Issues, creates
issues for Jules, and updates ticket status so users can track their reports in real-time.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("astrolink.feedback")

FEEDBACK_DIR = Path.home() / ".astrolink"
FEEDBACK_FILE = FEEDBACK_DIR / "feedback.json"


@dataclass
class FeedbackEntry:
    """A single feedback submission from a field user."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    category: str = "general"  # bug, performance, ui, suggestion, crash
    message: str = ""
    severity: str = "medium"  # low, medium, high, critical
    device_info: Optional[str] = None
    telemetry_snapshot: Optional[Dict[str, Any]] = None
    attachments: List[str] = field(default_factory=list)  # Stored attachment URLs/paths
    status: str = "pending"  # pending, triaged, in_progress, resolved
    resolved: bool = False
    jules_issue_number: Optional[int] = None
    jules_issue_url: Optional[str] = None
    resolution_notes: Optional[str] = None
    triaged_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class FeedbackManager:
    """Thread-safe feedback collection, status tracking, and retrieval."""

    def __init__(self, feedback_file: Path = FEEDBACK_FILE):
        self.feedback_file = feedback_file
        self.attachments_dir = feedback_file.parent / "attachments"
        self._lock = threading.RLock()
        self._ensure_storage()

    def _ensure_storage(self):
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        if not self.feedback_file.exists():
            self.feedback_file.write_text(json.dumps([], indent=2), encoding="utf-8")

    def _read_all(self) -> List[dict]:
        try:
            return json.loads(self.feedback_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_all(self, entries: List[dict]):
        """Atomically persist feedback so a crash cannot truncate the JSON store."""
        payload = json.dumps(entries, indent=2, ensure_ascii=False)
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="feedback-", suffix=".json", dir=self.feedback_file.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.feedback_file)
        finally:
            Path(temp_name).unlink(missing_ok=True)

    def submit(
        self,
        category: str,
        message: str,
        severity: str = "medium",
        device_info: Optional[str] = None,
        telemetry_snapshot: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[str]] = None,
    ) -> FeedbackEntry:
        """Submits a new feedback item with optional screenshot attachments."""
        category = str(category or "general").strip().lower()[:32]
        severity = str(severity or "medium").strip().lower()[:16]
        if severity not in {"low", "medium", "high", "critical"}:
            severity = "medium"
        message = str(message or "").strip()
        if not message:
            raise ValueError("Feedback message cannot be empty")
        if len(message) > 20_000:
            raise ValueError("Feedback message exceeds the 20,000 character limit")

        entry = FeedbackEntry(
            category=category,
            message=message,
            severity=severity,
            device_info=str(device_info)[:1_000] if device_info is not None else None,
            telemetry_snapshot=telemetry_snapshot if isinstance(telemetry_snapshot, dict) else {},
            status="pending",
        )

        saved_attachment_urls: List[str] = []
        if attachments:
            import base64
            if not isinstance(attachments, list) or len(attachments) > 3:
                raise ValueError("A feedback report may contain at most 3 attachments")
            for idx, item in enumerate(attachments):
                if not isinstance(item, str) or not item:
                    continue
                if item.startswith("data:image/") and ";base64," in item:
                    try:
                        header, b64_data = item.split(";base64,", 1)
                        # Reject oversized encoded data before decoding and require
                        # strict base64 to avoid memory/CPU abuse.
                        if len(b64_data) > 8 * 1024 * 1024:
                            raise ValueError("attachment is too large")
                        raw = base64.b64decode(b64_data, validate=True)
                        if len(raw) > 6 * 1024 * 1024:
                            raise ValueError("attachment is too large")
                        ext = "png"
                        if "jpeg" in header or "jpg" in header:
                            ext = "jpg"
                        elif "webp" in header:
                            ext = "webp"
                        filename = f"{entry.id}_ss_{idx + 1}.{ext}"
                        target = self.attachments_dir / filename
                        target.write_bytes(raw)
                        saved_attachment_urls.append(f"/api/feedback/attachment/{filename}")
                    except Exception as err:
                        logger.warning("Failed to decode attachment %d: %s", idx, err)
                elif item.startswith("/api/feedback/attachment/") and Path(item.rsplit("/", 1)[-1]).name == item.rsplit("/", 1)[-1]:
                    saved_attachment_urls.append(item)

        entry.attachments = saved_attachment_urls
        with self._lock:
            entries = self._read_all()
            entries.append(entry.to_dict())
            self._write_all(entries)
        logger.info(
            "Feedback submitted: [%s] %s (%s, %d attachments) — %s",
            entry.id, category, severity, len(entry.attachments), message[:60]
        )
        return entry

    def get_attachment_path(self, filename: str) -> Optional[Path]:
        """Resolves an attachment path safely preventing path traversal."""
        safe_name = Path(filename).name
        target = self.attachments_dir / safe_name
        if target.exists() and target.is_file():
            return target
        return None

    def get_all(self, include_resolved: bool = False) -> List[dict]:
        """Returns entries, optionally including resolved ones."""
        entries = self._read_all()
        if not include_resolved:
            entries = [e for e in entries if not e.get("resolved", False)]
        return entries

    def get_by_ids(self, feedback_ids: List[str]) -> List[dict]:
        """Returns specific feedback entries for user tracking, sorted latest first."""
        id_set = set(feedback_ids)
        entries = self._read_all()
        user_entries = [e for e in entries if e.get("id") in id_set]
        # Sort newest first
        user_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return user_entries

    def get_stats(self) -> dict:
        """Returns aggregated telemetry on pending, triaged, and resolved feedback."""
        entries = self._read_all()
        pending = [e for e in entries if e.get("status") == "pending"]
        triaged = [e for e in entries if e.get("status") in ("triaged", "in_progress")]
        resolved = [e for e in entries if e.get("resolved") or e.get("status") == "resolved"]
        categories = {}
        for e in entries:
            cat = e.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total": len(entries),
            "pending": len(pending),
            "triaged": len(triaged),
            "resolved": len(resolved),
            "by_category": categories,
        }

    def update_triage_status(
        self,
        feedback_id: str,
        status: str,
        issue_number: Optional[int] = None,
        issue_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Updates triage status and attaches GitHub issue details to prevent duplicates."""
        entries = self._read_all()
        updated = False
        for e in entries:
            if e.get("id") == feedback_id:
                e["status"] = status
                if issue_number is not None:
                    e["jules_issue_number"] = issue_number
                if issue_url:
                    e["jules_issue_url"] = issue_url
                if notes:
                    e["resolution_notes"] = notes
                if status == "resolved":
                    e["resolved"] = True
                elif status in ("triaged", "in_progress"):
                    e["triaged_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
                break
        if updated:
            self._write_all(entries)
        return updated

    def mark_resolved(self, feedback_id: str, issue_url: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """Marks a ticket as resolved by Jules."""
        return self.update_triage_status(
            feedback_id=feedback_id,
            status="resolved",
            issue_url=issue_url,
            notes=notes,
        )

    def clear_resolved(self) -> int:
        """Cleans up resolved feedback entries from active storage."""
        entries = self._read_all()
        original_count = len(entries)
        entries = [e for e in entries if not e.get("resolved", False)]
        self._write_all(entries)
        cleared = original_count - len(entries)
        logger.info("Cleared %d resolved feedback entries", cleared)
        return cleared

    def export_for_jules(self) -> List[dict]:
        """Exports ONLY pending, un-triaged feedback formatted for Jules issue creation.

        Prevents duplicate issue creation by skipping tickets that are already triaged or resolved.
        """
        entries = self._read_all()
        # Strictly only export pending items that don't have an issue yet
        pending = [
            e for e in entries
            if e.get("status") == "pending"
            and not e.get("jules_issue_number")
            and not e.get("resolved", False)
        ]
        issues = []
        for entry in pending:
            severity_label = {
                "critical": "priority: critical",
                "high": "priority: high",
                "medium": "priority: medium",
                "low": "priority: low",
            }.get(entry.get("severity", "medium"), "priority: medium")

            category_label = {
                "bug": "bug",
                "performance": "performance",
                "ui": "ui/ux",
                "suggestion": "enhancement",
                "crash": "bug",
            }.get(entry.get("category", "general"), "feedback")

            attachments_md = ""
            if entry.get("attachments"):
                attachments_md = "\n### Attached Screenshots & Diagnostics\n"
                for idx, att in enumerate(entry.get("attachments", [])):
                    attachments_md += f"- Screenshot {idx + 1}: `{att}`\n"

            title = f"[{entry.get('category', 'feedback').upper()}] {entry.get('message', '')[:80]}"
            body = f"""## User Feedback Report (Auto-Triaged)

**Feedback ID:** `{entry.get('id')}`
**Category:** {entry.get('category', 'general')}
**Severity:** {entry.get('severity', 'medium')}
**Submitted:** {entry.get('timestamp')}
**Device:** {entry.get('device_info', 'Unknown')}

### Description
{entry.get('message', 'No description provided.')}
{attachments_md}
### Telemetry Snapshot
```json
{json.dumps(entry.get('telemetry_snapshot') or {}, indent=2)}
```

### Instructions for Jules
Analyze this feedback, identify the root cause in the codebase, implement a fix, and submit a PR:
1. **Bug/Crash**: Find and fix the root cause. Add a regression test in `backend/`.
2. **Performance**: Profile and optimize hot loops. Ensure RAM stays under 200MB.
3. **UI/UX**: Fix visual issues following Apple HIG and OLED #000000 design standards.
4. **Enhancement**: Evaluate feasibility and implement if valuable.
"""
            issues.append({
                "feedback_id": entry.get("id"),
                "title": title,
                "body": body,
                "labels": [category_label, severity_label, "jules", "auto-triage"],
            })
        return issues


# Global singleton instance
feedback_manager = FeedbackManager()
