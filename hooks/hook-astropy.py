"""PyInstaller hook for astropy.

Prevents collecting astropy.visualization (which unconditionally imports matplotlib)
when matplotlib is excluded from the build bundle.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("astropy", filter=lambda name: "astropy.visualization" not in name)
