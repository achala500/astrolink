from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect submodules for astropy excluding astropy.visualization which requires matplotlib
hiddenimports = collect_submodules('astropy', filter=lambda name: not name.startswith('astropy.visualization'))
datas = collect_data_files('astropy')
excludedimports = ['astropy.visualization', 'matplotlib']
