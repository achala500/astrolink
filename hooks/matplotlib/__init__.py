"""Mock matplotlib module for PyInstaller dependency collection.

Prevents astropy.visualization.wcsaxes from raising a Skipped exception via
pytest.importorskip("matplotlib") during PyInstaller isolated child process collection.
"""

__version__ = "3.9.0"
