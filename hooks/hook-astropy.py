from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    'matplotlib',
    'astropy.visualization',
    'astropy.visualization.wcsaxes',
]

hiddenimports = (
    collect_submodules('astropy.io')
    + collect_submodules('astropy.config')
    + collect_submodules('astropy.utils')
    + collect_submodules('astropy.units')
    + collect_submodules('astropy.nddata')
    + collect_submodules('astropy.table')
)
