## 2025-05-18 - Path Traversal & Symlink Escape Prevention in Attachment Serving
**Vulnerability:** Attachment retrieval endpoint allowed potential path traversal or symlink escapes if file paths were not strictly resolved against base directory.
**Learning:** `Path(filename).name` strips directory path components, but does not resolve symlinks or nested path targets within directory trees.
**Prevention:** Always resolve both the base directory and the target path (`(base_dir / filename).resolve()`), then strictly verify `target.is_relative_to(base_dir.resolve())`.
