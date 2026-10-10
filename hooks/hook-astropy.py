from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization to prevent matplotlib import attempts during PyInstaller build
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)
excludedimports = ['astropy.visualization']
