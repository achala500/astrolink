"""PyInstaller custom hook for astropy.

Prevents collecting astropy.visualization submodules which require matplotlib
when matplotlib is excluded from the PyInstaller desktop bundle.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "visualization" not in name
)
