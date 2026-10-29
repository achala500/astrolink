"""Custom PyInstaller hook for astropy.

Filters out astropy.visualization submodules during PyInstaller binary analysis
to prevent pytest.importorskip("matplotlib") from raising Skipped exceptions in
isolated child process imports when matplotlib is excluded.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
