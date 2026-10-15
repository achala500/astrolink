"""Custom PyInstaller hook for astropy.

Filters out `astropy.visualization` submodules to avoid failing when
`matplotlib` is excluded.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "astropy.visualization" not in name,
)
