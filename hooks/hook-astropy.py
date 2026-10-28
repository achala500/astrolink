# PyInstaller hook for astropy
# Exclude astropy.visualization.wcsaxes if matplotlib is not installed to avoid pytest.importorskip failures

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('astropy', filter=lambda name: 'astropy.visualization.wcsaxes' not in name)
