from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization completely because it requires matplotlib (which is excluded from the desktop binary)
excludedmodules = ['astropy.visualization']

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: 'astropy.visualization' not in name,
    on_error='ignore'
)
