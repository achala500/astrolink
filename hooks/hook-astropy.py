"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization and astropy.visualization.wcsaxes to prevent
pytest.importorskip("matplotlib") from failing during collect_submodules.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Filter out visualization modules that depend on optional matplotlib
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "wcsaxes" not in name and "visualization" not in name,
)
datas = collect_data_files("astropy")
