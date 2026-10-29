"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization submodules (which trigger pytest.importorskip("matplotlib"))
from PyInstaller analysis and binary dependency collection.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
    "astropy.visualization.units",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

datas = [
    d for d in collect_data_files("astropy")
    if "visualization" not in d[0] and "visualization" not in d[1]
]
