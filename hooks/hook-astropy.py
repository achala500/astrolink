from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata, is_module_satisfies

# Exclude visualization modules that require matplotlib
excludedimports = ['astropy.visualization', 'astropy.visualization.wcsaxes']

# Collect data files excluding visualization
datas = [
    (src, dst) for src, dst in collect_data_files('astropy')
    if 'visualization' not in src
]

# Collect submodules using filter lambda to prevent importing astropy.visualization (which triggers pytest.importorskip("matplotlib"))
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)

ply_files = []
for path, target in collect_data_files('astropy', include_py_files=True):
    if path.endswith(('_parsetab.py', '_lextab.py')):
        ply_files.append((path, target))

datas += ply_files

if is_module_satisfies('astropy >= 5.0'):
    datas += copy_metadata('astropy')
    datas += copy_metadata('numpy')

hiddenimports += ['numpy.lib.recfunctions']
