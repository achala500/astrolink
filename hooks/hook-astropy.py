from PyInstaller.utils.hooks import collect_submodules

# Filter out astropy.visualization modules that require matplotlib when matplotlib is excluded
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)
