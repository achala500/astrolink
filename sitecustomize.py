"""Site customization for PyInstaller builds and runtime environment.

Mocks matplotlib if it is not installed so that astropy's pytest.importorskip("matplotlib")
calls do not raise Skipped exceptions during PyInstaller isolated child process analysis on Windows/Linux.
"""

import sys
from unittest.mock import MagicMock

if "matplotlib" not in sys.modules:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        sys.modules["matplotlib"] = MagicMock()
        sys.modules["matplotlib.pyplot"] = MagicMock()
