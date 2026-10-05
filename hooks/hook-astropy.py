from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Filter out astropy.visualization to prevent matplotlib import errors when matplotlib is excluded
hiddenimports = collect_submodules('astropy', filter=lambda name: 'visualization' not in name)
datas = collect_data_files('astropy')
