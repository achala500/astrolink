## 2026-10-03 - Path Traversal & Symlink Escapes in Dynamic Attachment Resolution
**Vulnerability:** `FeedbackManager.get_attachment_path()` checked `Path(filename).name` without canonical path resolution (`.resolve()`) or containment verification (`.is_relative_to()`), leaving attachment retrieval susceptible to symlink traversal outside `attachments_dir`.
**Learning:** `Path(filename).name` strips directory components, but if files or symlinks are present or constructed within `attachments_dir`, it can resolve to arbitrary files on disk.
**Prevention:** Always resolve the absolute canonical path using `Path.resolve()` and verify strict directory containment with `target.is_relative_to(base_dir)` before serving files.
