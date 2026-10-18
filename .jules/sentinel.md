## 2025-05-18 - Path Traversal Prevention in File Ingestion and Attachments
**Vulnerability:** Path traversal in `GPhotoTetherDaemon` (`.gphoto_events.txt` IPC log parsing) and `FeedbackManager.get_attachment_path`.
**Learning:** Parsing path strings directly from IPC log files or HTTP request parameters without checking `target.resolve().is_relative_to(base_dir.resolve())` allowed arbitrary file ingestion or access outside intended watch directories.
**Prevention:** Always convert candidate paths to absolute resolved paths with `.resolve()` and verify `target.is_relative_to(base_dir.resolve())` and `target.is_file()` before opening files.
