"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization from submodules and data files collection
to prevent import attempts of matplotlib when matplotlib is excluded.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect submodules while filtering out visualization modules that depend on matplotlib
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)

# Collect data files while excluding visualization data files
datas = [
    (src, dst) for src, dst in collect_data_files('astropy')
    if 'visualization' not in src and 'visualization' not in dst
]
