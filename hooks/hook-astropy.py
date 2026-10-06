"""Custom PyInstaller hook for astropy.

Filters out astropy.visualization to avoid build errors when matplotlib is excluded.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = ["astropy.visualization", "astropy.visualization.wcsaxes"]
hiddenimports = collect_submodules("astropy", filter=lambda name: "visualization" not in name)
datas = collect_data_files("astropy")
