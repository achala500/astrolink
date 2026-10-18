"""Custom PyInstaller hook for astropy.

Prevents build errors when matplotlib is excluded by filtering out astropy.visualization
which attempts to import matplotlib via pytest.importorskip("matplotlib").
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("astropy", filter=lambda name: "astropy.visualization" not in name)
datas = collect_data_files("astropy")
