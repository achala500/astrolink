"""Custom PyInstaller hook for Astropy.

Filters out `astropy.visualization` during submodule collection to prevent
PyInstaller from attempting to import `matplotlib` (which is excluded in astrolink.spec).
"""

from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "visualization" not in name,
)
