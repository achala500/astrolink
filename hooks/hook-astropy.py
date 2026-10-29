"""Custom PyInstaller hook for astropy.

Filters out astropy.visualization submodules during PyInstaller binary analysis
and monkeypatches pytest.importorskip to raise ImportError (instead of BaseException-derived
Skipped) so that astropy.visualization.wcsaxes catches missing matplotlib imports under
except Exception: without crashing PyInstaller isolated child process imports.
"""

import sys
from PyInstaller.utils.hooks import collect_submodules

try:
    import pytest

    def _safe_importorskip(modname, *args, **kwargs):
        if modname not in sys.modules:
            try:
                return __import__(modname)
            except Exception as exc:
                raise ImportError(f"Skipped import {modname}: {exc}") from exc
        return sys.modules[modname]

    pytest.importorskip = _safe_importorskip
except Exception:
    pass

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
