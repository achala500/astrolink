from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Filter out astropy.visualization to prevent matplotlib import errors when matplotlib is excluded
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
datas = collect_data_files("astropy")
