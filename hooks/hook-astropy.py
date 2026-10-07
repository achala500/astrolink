"""Custom PyInstaller hook for astropy.

Filters out astropy.visualization to prevent PyInstaller collection failures
when matplotlib is not installed.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "visualization" not in name,
)
datas = collect_data_files("astropy")
excludedimports = ["astropy.visualization", "matplotlib"]
