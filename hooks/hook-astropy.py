"""Custom PyInstaller hook for astropy.

Filters out astropy.visualization submodules (which invoke pytest.importorskip("matplotlib"))
to prevent PyInstaller build failures when matplotlib is excluded.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
