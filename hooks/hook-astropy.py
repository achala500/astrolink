"""PyInstaller hook for astropy.

When matplotlib is in PyInstaller's excludes list, astropy's default hook calls
collect_submodules('astropy'), which attempts to import astropy.visualization.wcsaxes,
which in turn calls pytest.importorskip('matplotlib') and causes PyInstaller build failure.

This hook filters out astropy.visualization submodules to prevent attempting to collect matplotlib-dependent modules.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
