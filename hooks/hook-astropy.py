"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization modules that depend on matplotlib,
preventing PyInstaller from attempting to import matplotlib during collection.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Exclude visualization modules that require matplotlib
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

# Collect submodules with on_error="ignore" and filter out astropy.visualization
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
    on_error="ignore",
)

# Collect data files, filtering out any visualization data
datas = [
    (src, dst) for src, dst in collect_data_files("astropy")
    if "visualization" not in src
]
