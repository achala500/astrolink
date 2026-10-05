## 2026-10-05 - Path Traversal Boundary Validation with `pathlib.Path.name`
**Vulnerability:** Attachment file serving in `FeedbackManager.get_attachment_path()` relied on `Path(filename).name` alone without resolving the target path and checking `is_relative_to(base_dir)`.
**Learning:** In Python's `pathlib.Path`, `Path("..").name` evaluates to `".."` rather than an empty string or stripping directory traversal markers. Concatenating `base_dir / Path("..").name` resolves to `base_dir.parent`, escaping the intended directory boundary.
**Prevention:** Always sanitize input by rejecting `.`/`..`, resolve the target path using `.resolve()`, and strictly verify `target.is_relative_to(base_dir.resolve())` before accessing files.
