"""Custom PyInstaller hook for astropy to exclude matplotlib visualization dependencies."""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
    is_module_satisfies,
)

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

# Collect submodules of astropy, filtering out visualization modules to avoid matplotlib import
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

# In Cython code, Astropy imports numpy.lib.recfunctions
hiddenimports.append("numpy.lib.recfunctions")

# Exclude visualization data files
datas = [
    d for d in collect_data_files("astropy")
    if "visualization" not in d[1]
]

ply_files = []
for path, target in collect_data_files("astropy", include_py_files=True):
    if path.endswith(("_parsetab.py", "_lextab.py")):
        ply_files.append((path, target))

datas += ply_files

if is_module_satisfies("astropy >= 5.0"):
    datas += copy_metadata("astropy")
    datas += copy_metadata("numpy")
