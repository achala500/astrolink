"""PyInstaller hook for astropy.

Excludes astropy.visualization to prevent build failures when matplotlib is excluded
and wcsaxes attempts to run pytest.importorskip("matplotlib").
"""

from PyInstaller.utils.hooks import collect_submodules

excludedimports = ["astropy.visualization"]
hiddenimports = collect_submodules("astropy", filter=lambda name: "astropy.visualization" not in name)
