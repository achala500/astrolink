"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization from submodule collection and imports because
astropy.visualization requires matplotlib, which is excluded from the application.
"""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)

excludedimports = [
    'astropy.visualization',
    'astropy.visualization.wcsaxes',
]
