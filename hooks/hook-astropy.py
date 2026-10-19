from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    'astropy.visualization',
    'astropy.visualization.wcsaxes',
    'matplotlib',
]

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: 'astropy.visualization' not in name,
)
