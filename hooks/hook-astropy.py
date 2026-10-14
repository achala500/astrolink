from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization because it unconditionally imports matplotlib
hiddenimports = collect_submodules('astropy', filter=lambda name: 'astropy.visualization' not in name)
