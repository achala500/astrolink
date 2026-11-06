"""Custom PyInstaller hook for astropy to exclude matplotlib-dependent submodules."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules("astropy", filter=lambda name: not name.startswith("astropy.visualization"))
datas = collect_data_files("astropy")
