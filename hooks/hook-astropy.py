from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('astropy')
hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)
