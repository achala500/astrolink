"""Triage user feedback into GitHub Issues for Jules autonomous resolution.

Reads feedback from the local feedback.json file (committed or fetched),
creates GitHub Issues, and marks them for Jules processing.
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "achala500/astrolink")
API_BASE = "https://api.github.com"


def create_github_issue(title: str, body: str, labels: list[str]) -> dict:
    """Creates a GitHub Issue via the REST API."""
    url = f"{API_BASE}/repos/{REPO}/issues"
    payload = json.dumps({
        "title": title,
        "body": body,
        "labels": labels,
    }).encode("utf-8")

    req = Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"Failed to create issue: {e}")
        return {}


def load_feedback() -> list[dict]:
    """Loads feedback from the local feedback file."""
    feedback_file = Path.home() / ".astrolink" / "feedback.json"
    
    # Also check the repo root for CI environments
    alt_file = Path("feedback_export.json")
    
    for f in [feedback_file, alt_file]:
        if f.exists():
            try:
                entries = json.loads(f.read_text(encoding="utf-8"))
                # Filter unresolved
                return [e for e in entries if not e.get("resolved", False)]
            except (json.JSONDecodeError, FileNotFoundError):
                continue
    return []


def main():
    feedback = load_feedback()
    if not feedback:
        print("No unresolved feedback to triage. All clear!")
        return

    print(f"Found {len(feedback)} unresolved feedback entries.")
    created = 0

    for entry in feedback:
        category = entry.get("category", "general")
        severity = entry.get("severity", "medium")
        message = entry.get("message", "No description")
        feedback_id = entry.get("id", "unknown")
        timestamp = entry.get("timestamp", "")
        device = entry.get("device_info", "Unknown")
        telemetry = entry.get("telemetry_snapshot", {})

        severity_label = f"priority: {severity}"
        category_label = {
            "bug": "bug",
            "performance": "performance",
            "ui": "ui/ux",
            "suggestion": "enhancement",
            "crash": "bug",
        }.get(category, "feedback")

        title = f"[{category.upper()}] {message[:80]}"
        body = f"""## User Feedback Report (Auto-Triaged)

**Feedback ID:** `{feedback_id}`
**Category:** {category}
**Severity:** {severity}
**Submitted:** {timestamp}
**Device:** {device}

---

### Description
{message}

### Telemetry at Time of Report
```json
{json.dumps(telemetry, indent=2)}
```

---

### Jules Instructions
@jules — Please analyze and fix this issue:

1. **Bug/Crash**: Find root cause, implement fix, add regression test
2. **Performance**: Profile the pipeline, optimize hot paths, verify RAM < 200MB
3. **UI/UX**: Fix visual issues following Apple HIG + OLED `#000000` standards
4. **Enhancement**: Evaluate feasibility, implement if valuable, update tests

After fixing, run `python -m pytest backend/ -v` to verify all tests pass.
"""
        labels = [category_label, severity_label, "jules", "auto-triage"]

        result = create_github_issue(title, body, labels)
        if result.get("number"):
            print(f"  Created issue #{result['number']}: {title}")
            created += 1
        else:
            print(f"  Failed to create issue for feedback {feedback_id}")

    print(f"\nTriage complete: {created}/{len(feedback)} issues created.")


if __name__ == "__main__":
    main()
