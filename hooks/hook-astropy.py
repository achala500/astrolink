"""Custom PyInstaller hook for astropy.

Prevents hook-astropy from running collect_submodules('astropy') which imports
astropy.visualization.wcsaxes and fails when matplotlib is excluded.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization'),
)
excludes = ['astropy.visualization']
