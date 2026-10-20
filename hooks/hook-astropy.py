from PyInstaller.utils.hooks import collect_submodules

# Collect submodules of astropy but exclude astropy.visualization to avoid matplotlib dependency failure
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization'),
)
