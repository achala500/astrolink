"""Feedback collection system for AstroLink.

Stores user-submitted feedback (bugs, suggestions, performance issues) in a local JSON file.
A scheduled GitHub Action reads this data, creates GitHub Issues, and assigns them to Jules
for autonomous resolution.
"""

from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

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
    resolved: bool = False
    jules_issue_url: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class FeedbackManager:
    """Thread-safe feedback collection and retrieval."""

    def __init__(self, feedback_file: Path = FEEDBACK_FILE):
        self.feedback_file = feedback_file
        self._ensure_storage()

    def _ensure_storage(self):
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.feedback_file.exists():
            self.feedback_file.write_text(json.dumps([], indent=2))

    def _read_all(self) -> List[dict]:
        try:
            return json.loads(self.feedback_file.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_all(self, entries: List[dict]):
        self.feedback_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')

    def submit(self, category: str, message: str, severity: str = "medium",
               device_info: Optional[str] = None,
               telemetry_snapshot: Optional[Dict[str, Any]] = None) -> FeedbackEntry:
        entry = FeedbackEntry(
            category=category,
            message=message,
            severity=severity,
            device_info=device_info,
            telemetry_snapshot=telemetry_snapshot,
        )
        entries = self._read_all()
        entries.append(entry.to_dict())
        self._write_all(entries)
        logger.info("Feedback submitted: [%s] %s — %s", entry.id, category, message[:80])
        return entry

    def get_all(self, include_resolved: bool = False) -> List[dict]:
        entries = self._read_all()
        if not include_resolved:
            entries = [e for e in entries if not e.get('resolved', False)]
        return entries

    def get_stats(self) -> dict:
        entries = self._read_all()
        unresolved = [e for e in entries if not e.get('resolved', False)]
        categories = {}
        for e in unresolved:
            cat = e.get('category', 'general')
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total": len(entries),
            "unresolved": len(unresolved),
            "resolved": len(entries) - len(unresolved),
            "by_category": categories,
        }

    def mark_resolved(self, feedback_id: str, issue_url: Optional[str] = None) -> bool:
        entries = self._read_all()
        for e in entries:
            if e.get('id') == feedback_id:
                e['resolved'] = True
                e['jules_issue_url'] = issue_url
                self._write_all(entries)
                return True
        return False

    def clear_resolved(self) -> int:
        entries = self._read_all()
        original_count = len(entries)
        entries = [e for e in entries if not e.get('resolved', False)]
        self._write_all(entries)
        cleared = original_count - len(entries)
        logger.info("Cleared %d resolved feedback entries", cleared)
        return cleared

    def export_for_jules(self) -> List[dict]:
        """Exports unresolved feedback formatted for Jules issue creation."""
        unresolved = self.get_all(include_resolved=False)
        issues = []
        for entry in unresolved:
            severity_label = {
                'critical': 'priority: critical',
                'high': 'priority: high',
                'medium': 'priority: medium',
                'low': 'priority: low',
            }.get(entry.get('severity', 'medium'), 'priority: medium')

            category_label = {
                'bug': 'bug',
                'performance': 'performance',
                'ui': 'ui/ux',
                'suggestion': 'enhancement',
                'crash': 'bug',
            }.get(entry.get('category', 'general'), 'feedback')

            title = f"[{entry.get('category', 'feedback').upper()}] {entry.get('message', '')[:80]}"
            body = f"""## User Feedback Report

**ID:** `{entry.get('id')}`
**Category:** {entry.get('category', 'general')}
**Severity:** {entry.get('severity', 'medium')}
**Submitted:** {entry.get('timestamp')}
**Device:** {entry.get('device_info', 'Unknown')}

### Description
{entry.get('message', 'No description provided.')}

### Telemetry Snapshot
```json
{{json.dumps(entry.get('telemetry_snapshot') or {{}}, indent=2)}}
```

### Instructions for Jules
Analyze this feedback, identify the root cause in the codebase, implement a fix, and submit a PR.
Focus on:
1. If bug: Find and fix the root cause. Add a regression test.
2. If performance: Profile and optimize. Ensure RAM stays under 200MB.
3. If UI: Fix the visual issue following Apple HIG and OLED #000000 design standards.
4. If suggestion: Evaluate feasibility and implement if valuable.
"""
            issues.append({
                'feedback_id': entry.get('id'),
                'title': title,
                'body': body,
                'labels': [category_label, severity_label, 'jules', 'auto-triage'],
            })
        return issues


# Singleton instance
feedback_manager = FeedbackManager()
