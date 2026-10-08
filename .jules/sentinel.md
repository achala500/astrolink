## 2026-10-08 - PyInstaller Astropy matplotlib dependency crash
**Vulnerability:** Build failure in desktop executable packaging when matplotlib is excluded from the bundle.
**Learning:** `collect_submodules('astropy')` in PyInstaller attempts to import `astropy.visualization.wcsaxes`, which invokes `pytest.importorskip("matplotlib")` and raises `Skipped` error if `matplotlib` is excluded.
**Prevention:** Use custom hook `hooks/hook-astropy.py` with `collect_submodules('astropy', filter=lambda name: not name.startswith('astropy.visualization'))` and load via `hookspath=['hooks']` in `astrolink.spec`.
