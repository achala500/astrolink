"""Custom PyInstaller hook for Astropy.

Filters out `astropy.visualization` submodules to avoid build failures
when `matplotlib` is excluded or missing.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
excludedimports = ["matplotlib", "astropy.visualization"]
