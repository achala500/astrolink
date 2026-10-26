"""Dummy matplotlib module for PyInstaller build compatibility.

Prevents astropy's pytest.importorskip("matplotlib") from raising Skipped exceptions
during PyInstaller analysis and binary dependency collection.
"""

__version__ = "3.10.0"
