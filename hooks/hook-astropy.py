"""Custom PyInstaller hook for astropy to exclude astropy.visualization when matplotlib is omitted."""

from PyInstaller.utils.hooks import collect_submodules

# Collect astropy submodules but exclude astropy.visualization which requires matplotlib
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
