## 2025-05-18 - Prevent Path Traversal in IPC Event Log Ingestion
**Vulnerability:** `GPhotoTetherDaemon._worker()` accepted unvalidated relative or absolute file paths read from IPC log `.gphoto_events.txt`, allowing arbitrary file ingestion outside the designated watch directory into RAM buffers and telemetry streaming.
**Learning:** Checking `target_path.exists()` is insufficient to prevent path traversal when processing paths provided by external hooks or IPC logs.
**Prevention:** Always resolve target paths (`target.resolve()`) and explicitly enforce `target.resolve().is_relative_to(base_dir.resolve())` before opening or ingesting files.
