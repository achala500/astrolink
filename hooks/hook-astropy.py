"""Custom PyInstaller hook for astropy.

Prevents collecting astropy.visualization.wcsaxes which invokes
pytest.importorskip("matplotlib") and breaks builds when matplotlib is not installed.
"""

from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    'astropy.visualization',
    'astropy.visualization.wcsaxes',
]

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)
