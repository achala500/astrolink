"""Custom PyInstaller hook for astropy.

Filters out astropy.visualization submodules to avoid optional matplotlib dependencies
triggering pytest.importorskip errors during PyInstaller module collection.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
datas = collect_data_files("astropy")
