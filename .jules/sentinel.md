## 2026-10-07 - Strict Path Traversal and Symlink Escape Prevention in Attachment Resolution
**Vulnerability:** `Path(filename).name` was used to resolve attachment paths in `FeedbackManager.get_attachment_path`, which prevented basic path traversal via filenames containing directory separators, but could fail on non-standard paths or symlinks pointing outside the `attachments_dir`.
**Learning:** Simply calling `Path(filename).name` stripped directory path components but did not prevent symbolic links created within `attachments_dir` from pointing to files outside the directory.
**Prevention:** Always resolve the base directory and the target path using `.resolve()`, then verify `target.is_relative_to(base_dir)` alongside existence checks before serving or accessing files.
