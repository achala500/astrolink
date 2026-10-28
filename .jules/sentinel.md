## 2026-10-28 - Path Traversal & Symlink Escape Prevention in Attachment Serving
**Vulnerability:** `get_attachment_path` in `FeedbackManager` checked file existence using `self.attachments_dir / safe_name` without resolving symlinks or checking relative directory bounds.
**Learning:** `Path(filename).name` strips directory separators from the input string, but does not prevent symbolic links placed inside the directory from resolving to external targets on the filesystem.
**Prevention:** Always use `target = (base_dir / safe_name).resolve()` and verify `target.is_relative_to(base_dir.resolve())` before opening or returning file paths for HTTP file serving responses.
