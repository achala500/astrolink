from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization to prevent pytest.importorskip("matplotlib") failures
# when building desktop binaries in environments without matplotlib.
excludedimports = ['astropy.visualization', 'astropy.visualization.wcsaxes']

hiddenimports = collect_submodules('astropy', filter=lambda name: not name.startswith('astropy.visualization'))
