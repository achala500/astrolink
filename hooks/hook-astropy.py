"""Custom PyInstaller hook for astropy.

Prevents collect_submodules('astropy') from traversing into astropy.visualization
and astropy.visualization.wcsaxes, which call `pytest.importorskip("matplotlib")`
and fail when matplotlib is not installed.
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

datas = collect_data_files("astropy")
# Filter out any visualization data files
datas = [d for d in datas if "visualization" not in d[0] and "visualization" not in d[1]]
