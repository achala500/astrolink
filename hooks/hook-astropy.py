from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: 'astropy.visualization' not in name
)
