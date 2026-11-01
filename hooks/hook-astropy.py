"""Custom PyInstaller hook for Astropy.

Overrides the default contrib hook to exclude astropy.visualization
which triggers pytest.importorskip("matplotlib") when matplotlib is excluded.
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
    is_module_satisfies,
)

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
    "matplotlib",
]

# Astropy includes non-Python files that need to be present at runtime
datas = [
    d for d in collect_data_files("astropy")
    if not any(x in d[0] for x in ["visualization"])
]

# Collect submodules while excluding visualization and ignoring optional imports
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "visualization" not in name and "matplotlib" not in name,
    on_error="ignore",
)

# Include *_parsetab.py and *_lextab.py files
ply_files = []
for path, target in collect_data_files("astropy", include_py_files=True):
    if path.endswith(("_parsetab.py", "_lextab.py")):
        ply_files.append((path, target))

datas += ply_files

if is_module_satisfies("astropy >= 5.0"):
    datas += copy_metadata("astropy")
    datas += copy_metadata("numpy")

hiddenimports += ["numpy.lib.recfunctions"]
