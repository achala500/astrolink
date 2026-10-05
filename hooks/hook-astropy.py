from PyInstaller.utils.hooks import collect_submodules, collect_data_files

excludedimports = ['astropy.visualization', 'astropy.visualization.wcsaxes']
hiddenimports = collect_submodules('astropy', filter=lambda name: 'visualization' not in name)
datas = collect_data_files('astropy', excludes=['astropy.visualization', 'astropy.visualization.wcsaxes'])
