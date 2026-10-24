"""PyInstaller custom hook for astropy.

Prevents hook failures when matplotlib is excluded by filtering out astropy.visualization
submodules that depend on matplotlib.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Filter out astropy.visualization submodules to avoid optional matplotlib dependency crash
hiddenimports = [
    mod for mod in collect_submodules('astropy', filter=lambda name: not name.startswith('astropy.visualization'))
]
datas = collect_data_files('astropy')
