"""Custom PyInstaller hook for astropy.

Prevents pytest.importorskip("matplotlib") inside astropy.visualization.wcsaxes
from triggering a Skipped exception during collect_submodules("astropy") when
matplotlib is excluded.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

datas = collect_data_files(
    "astropy",
    excludes=["**/visualization/**"],
)
