"""PyInstaller custom hook for astropy.

Mocks matplotlib during module collection so that pytest.importorskip("matplotlib")
inside astropy.visualization.wcsaxes does not raise a Skipped exception when matplotlib is excluded.
"""

import sys
from unittest.mock import MagicMock

if "matplotlib" not in sys.modules:
    sys.modules["matplotlib"] = MagicMock()
    sys.modules["matplotlib.pyplot"] = MagicMock()
