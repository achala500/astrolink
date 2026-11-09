"""Custom PyInstaller hook for astropy.

Prevents astropy.visualization.wcsaxes from attempting to import matplotlib,
which raises pytest.importorskip("matplotlib") during PyInstaller Analysis
when matplotlib is excluded or not installed.
"""

from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules("astropy", filter=lambda name: not name.startswith("astropy.visualization"))
