"""Custom PyInstaller hook for Astropy.

Filters out `astropy.visualization` submodules to avoid build failures
when optional dependency `matplotlib` is excluded/not installed.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "astropy.visualization" not in name,
)
