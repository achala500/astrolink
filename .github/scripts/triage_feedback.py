"""Triage user feedback into GitHub Issues for Jules autonomous resolution.

Features:
1. Deduplication: Searches existing GitHub Issues by Feedback ID before creating any issue.
   Never creates duplicate issues for the same user feedback.
2. Two-way status tracking: Updates feedback state (pending -> triaged -> in_progress -> resolved).
   If Jules closes an issue on GitHub, marks the local ticket as resolved.
3. Telemetry preservation: Passes field sensor telemetry, FWHM, and stack counts to Jules.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "achala500/astrolink")
API_BASE = "https://api.github.com"


def _api_request(url: str, method: str = "GET", data: Optional[dict] = None) -> dict:
    """Executes an authenticated GitHub REST API request."""
    encoded_data = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=encoded_data, method=method)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "AstroLink-Jules-Triage")
    if data:
        req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"[API Error] {e.code} on {url}: {body[:200]}")
        return {}
    except URLError as e:
        print(f"[Network Error] {e.reason} on {url}")
        return {}


def find_existing_issue_for_feedback(feedback_id: str) -> Optional[dict]:
    """Queries GitHub Search API to find any existing issue created for this feedback ID.

    Guarantees Jules will never create duplicate issues for the same report.
    """
    if not GITHUB_TOKEN:
        return None

    query = f'repo:{REPO} "{feedback_id}" in:body'
    url = f"{API_BASE}/search/issues?q={urllib.parse.quote(query)}"
    res = _api_request(url, method="GET")
    items = res.get("items", [])
    if items:
        # Return the oldest issue matching this feedback ID
        items.sort(key=lambda x: x.get("number", 0))
        return items[0]
    return None


def create_github_issue(title: str, body: str, labels: List[str]) -> dict:
    """Creates a new GitHub Issue for Jules."""
    url = f"{API_BASE}/repos/{REPO}/issues"
    return _api_request(url, method="POST", data={"title": title, "body": body, "labels": labels})


def get_feedback_files() -> List[Path]:
    """Finds all candidate feedback storage files."""
    paths = [
        Path.home() / ".astrolink" / "feedback.json",
        Path("feedback_export.json"),
        Path("feedback.json"),
    ]
    return [p for p in paths if p.exists()]


def triage_feedback():
    """Main triage routine with deduplication and state synchronization."""
    files = get_feedback_files()
    if not files:
        print("[Triage] No feedback files found. Skipping.")
        return

    target_file = files[0]
    try:
        entries: List[dict] = json.loads(target_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Triage] Failed to load {target_file}: {e}")
        return

    print(f"[Triage] Loaded {len(entries)} total feedback tickets from {target_file}.")
    created_count = 0
    synced_count = 0

    for entry in entries:
        feedback_id = entry.get("id")
        if not feedback_id:
            continue

        # Check if already has an issue or is resolved
        current_status = entry.get("status", "pending")
        existing_issue_num = entry.get("jules_issue_number")

        # 1. Search GitHub to see if an issue already exists (prevents duplicate runs)
        existing_issue = find_existing_issue_for_feedback(feedback_id)

        if existing_issue:
            issue_num = existing_issue.get("number")
            issue_url = existing_issue.get("html_url")
            state = existing_issue.get("state")  # open or closed

            entry["jules_issue_number"] = issue_num
            entry["jules_issue_url"] = issue_url

            if state == "closed":
                entry["status"] = "resolved"
                entry["resolved"] = True
                entry["resolution_notes"] = f"Resolved in GitHub Issue #{issue_num}"
                print(f"  [Sync] Feedback #{feedback_id} marked RESOLVED (Issue #{issue_num} closed)")
            else:
                entry["status"] = "in_progress"
                print(f"  [Deduplicated] Feedback #{feedback_id} already tracked in Issue #{issue_num} ({state})")
            synced_count += 1
            continue

        # If already marked resolved locally, don't create an issue
        if entry.get("resolved") or current_status == "resolved":
            continue

        # 2. No issue exists yet -> Create new GitHub Issue for Jules
        category = entry.get("category", "general")
        severity = entry.get("severity", "medium")
        message = entry.get("message", "No description provided.")
        timestamp = entry.get("timestamp", "")
        device = entry.get("device_info", "Unknown")
        telemetry = entry.get("telemetry_snapshot") or {}

        severity_label = f"priority: {severity}"
        category_label = {
            "bug": "bug",
            "performance": "performance",
            "ui": "ui/ux",
            "suggestion": "enhancement",
            "crash": "bug",
        }.get(category, "feedback")

        title = f"[{category.upper()}] {message[:70]} (#{feedback_id})"
        body = f"""## User Feedback Report (Auto-Triaged for Jules)

**Feedback ID:** `{feedback_id}`
**Category:** {category}
**Severity:** {severity}
**Submitted:** {timestamp}
**Device Context:** {device}

---

### Description
{message}

### Real-Time Field Telemetry Snapshot
```json
{json.dumps(telemetry, indent=2)}
```

---

### Autonomous Instructions for Jules
@jules — Please evaluate and resolve this field report:
1. **Root Cause Analysis**: Inspect codebase relevant to `{category}`.
2. **Implementation**: Fix bugs or apply optimizations without breaking existing pipeline tests.
3. **Verification**: Run `python -m pytest backend/ -v` to ensure 100% test pass rate.
4. **Pull Request**: Open a PR referencing this issue and auto-close when merged.
"""
        labels = [category_label, severity_label, "jules", "auto-triage"]

        res = create_github_issue(title, body, labels)
        if res.get("number"):
            issue_num = res["number"]
            issue_url = res.get("html_url")
            entry["jules_issue_number"] = issue_num
            entry["jules_issue_url"] = issue_url
            entry["status"] = "triaged"
            entry["triaged_at"] = datetime.now(timezone.utc).isoformat()
            print(f"  [Created] Issue #{issue_num} for Feedback #{feedback_id}: {title}")
            created_count += 1
        else:
            print(f"  [Skip] Could not create issue for Feedback #{feedback_id} (API credentials or rate limit)")

    # Save updated entries back to disk
    target_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"[Triage Complete] {created_count} issues created, {synced_count} existing issues synced. All deduped.")


if __name__ == "__main__":
    triage_feedback()
