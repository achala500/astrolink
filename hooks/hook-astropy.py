from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
    is_module_satisfies,
)

# Astropy includes a number of non-Python files that need to be present at runtime
datas = [
    (src, dst)
    for src, dst in collect_data_files('astropy')
    if not any(part in src for part in ('visualization', 'wcsaxes'))
]

# Exclude astropy.visualization submodules to avoid matplotlib dependency failure
excludedimports = [
    'astropy.visualization',
    'astropy.visualization.wcsaxes',
]

# Collect submodules, filtering out visualization
hiddenimports = [
    mod
    for mod in collect_submodules(
        'astropy',
        filter=lambda name: not name.startswith('astropy.visualization')
    )
]

ply_files = []
for path, target in collect_data_files('astropy', include_py_files=True):
    if path.endswith(('_parsetab.py', '_lextab.py')):
        ply_files.append((path, target))

datas += ply_files

if is_module_satisfies('astropy >= 5.0'):
    datas += copy_metadata('astropy')
    datas += copy_metadata('numpy')

hiddenimports += ['numpy.lib.recfunctions']
