"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization to prevent build failures when matplotlib is not installed.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
