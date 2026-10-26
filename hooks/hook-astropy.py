import sys
import types

# Mock matplotlib in sys.modules so pytest.importorskip("matplotlib") inside astropy.visualization
# does not raise a Skipped exception during PyInstaller's astropy analysis when matplotlib is excluded.
if "matplotlib" not in sys.modules:
    mock_matplotlib = types.ModuleType("matplotlib")
    mock_matplotlib.__version__ = "3.10.0"
    sys.modules["matplotlib"] = mock_matplotlib
