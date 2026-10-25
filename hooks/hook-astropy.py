"""Custom PyInstaller hook for astropy.

Prevents astropy.visualization.wcsaxes (or other visualization modules) from attempting to import
matplotlib during PyInstaller's analysis and binary dependency collection stages when matplotlib is excluded.
"""

import sys
import unittest.mock
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Create dummy mock module for matplotlib with __version__ attribute to prevent pytest.importorskip("matplotlib")
# from throwing Skipped exception during PyInstaller module graph traversal.
mock_matplotlib = unittest.mock.MagicMock()
mock_matplotlib.__version__ = "3.10.0"
sys.modules["matplotlib"] = mock_matplotlib
sys.modules["matplotlib.pyplot"] = unittest.mock.MagicMock()

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization'),
)
datas = collect_data_files('astropy', excludes=['**/visualization/**'])
excludes = ['astropy.visualization', 'matplotlib']
