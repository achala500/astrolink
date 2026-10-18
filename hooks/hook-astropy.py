from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization submodules because wcsaxes requires matplotlib which is excluded
hiddenimports = collect_submodules("astropy", filter=lambda name: not name.startswith("astropy.visualization"))
