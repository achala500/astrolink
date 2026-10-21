from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization'),
    on_error='ignore'
)
excludedimports = ['astropy.visualization']
