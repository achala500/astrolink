# Sentinel Security Journal

## 2026-03-30 - Path Traversal Prevention in Attachment Resolution
**Vulnerability:** Path traversal risk in `FeedbackManager.get_attachment_path`.
**Learning:** `Path(filename).name` stripped directory separators, but using `target = (self.attachments_dir / filename).resolve()` with `target.is_relative_to(base_dir)` provides robust boundary validation against relative traversal vectors (`../`, `..%2F`) while allowing safe relative sub-paths if intended.
**Prevention:** Always resolve target and base paths and verify `target.is_relative_to(base_dir)` before serving or opening local files.
