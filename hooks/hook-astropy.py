"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization from submodules collection to prevent
import attempts of matplotlib when matplotlib is excluded from the build.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect submodules while filtering out visualization modules that depend on matplotlib
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)

datas = collect_data_files('astropy')
