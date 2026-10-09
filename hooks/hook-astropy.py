from PyInstaller.utils.hooks import collect_submodules

# Collect astropy submodules, excluding astropy.visualization which requires matplotlib
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: 'astropy.visualization' not in name
)
