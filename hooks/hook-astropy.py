"""Custom PyInstaller hook for astropy.

Filters out `astropy.visualization` submodules to prevent PyInstaller from attempting
to import optional dependencies like `matplotlib` during static analysis.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization")
)
