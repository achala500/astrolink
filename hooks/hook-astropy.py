"""Custom PyInstaller hook for astropy.

Prevents astropy.visualization.wcsaxes (or other visualization modules) from attempting to import
matplotlib during PyInstaller's analysis AND child process binary dependency collection stages
when matplotlib is excluded.
"""

import sys
import types
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Dummy matplotlib module with dummy submodules to safely satisfy pytest.importorskip("matplotlib")
# both during hook execution and during child process dependency tracing.
class _DummyModule(types.ModuleType):
    __version__ = "3.10.0"

    def __getattr__(self, name):
        return _DummyModule(name)

dummy_mpl = _DummyModule("matplotlib")
dummy_mpl.pyplot = _DummyModule("matplotlib.pyplot")

sys.modules["matplotlib"] = dummy_mpl
sys.modules["matplotlib.pyplot"] = dummy_mpl.pyplot

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization'),
)
datas = collect_data_files('astropy', excludes=['**/visualization/**'])
excludes = ['astropy.visualization', 'matplotlib']
