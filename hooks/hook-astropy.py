# ------------------------------------------------------------------
# Custom PyInstaller hook for astropy in AstroLink
# Prevents collect_submodules('astropy') from traversing into
# astropy.visualization.wcsaxes, which fails when matplotlib is absent.
# ------------------------------------------------------------------

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
    is_module_satisfies,
)

# Exclude visualization modules that require matplotlib
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

# Astropy non-Python data files
raw_datas = collect_data_files("astropy")
datas = [d for d in raw_datas if "visualization" not in d[0]]

# Collect submodules while explicitly filtering out astropy.visualization
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

# Parsing tables
ply_files = []
for path, target in collect_data_files("astropy", include_py_files=True):
    if path.endswith(("_parsetab.py", "_lextab.py")):
        ply_files.append((path, target))

datas += ply_files

if is_module_satisfies("astropy >= 5.0"):
    datas += copy_metadata("astropy")
    datas += copy_metadata("numpy")

hiddenimports += ["numpy.lib.recfunctions"]
