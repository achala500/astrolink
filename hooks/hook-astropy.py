"""Custom PyInstaller hook for astropy.

Prevents collecting astropy.visualization and astropy.visualization.wcsaxes,
which call pytest.importorskip("matplotlib") and fail when matplotlib is excluded.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

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
