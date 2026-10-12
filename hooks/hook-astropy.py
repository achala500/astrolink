from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Filter out astropy.visualization to prevent matplotlib import errors during pyinstaller build
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)

datas = collect_data_files('astropy')
