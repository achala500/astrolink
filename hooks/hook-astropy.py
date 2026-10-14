"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization submodules during submodule collection
to avoid build failures when matplotlib is excluded from the build.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "astropy.visualization" not in name,
)
