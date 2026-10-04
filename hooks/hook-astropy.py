from PyInstaller.utils.hooks import collect_submodules

# Filter out astropy.visualization submodules to prevent wcsaxes importing missing matplotlib
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)
