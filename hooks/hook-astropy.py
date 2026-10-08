from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization to prevent matplotlib import attempt during PyInstaller build
hiddenimports = collect_submodules('astropy', filter=lambda name: 'astropy.visualization' not in name)
