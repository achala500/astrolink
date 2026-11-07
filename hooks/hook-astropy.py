# PyInstaller hook for astropy
# Exclude visualization modules that require matplotlib when running in headless/desktop mode
from PyInstaller.utils.hooks import collect_submodules

excludedimports = ['astropy.visualization', 'astropy.visualization.wcsaxes']
hiddenimports = collect_submodules('astropy', filter=lambda name: not name.startswith('astropy.visualization'))
