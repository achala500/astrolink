"""Custom PyInstaller hook for astropy to exclude matplotlib visualization dependencies."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Exclude visualization packages that require matplotlib
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
    "matplotlib",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

datas = collect_data_files(
    "astropy",
    excludes=["**/visualization/**"],
)
