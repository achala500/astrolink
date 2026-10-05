from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Filter out astropy submodules that require optional matplotlib dependency
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization.wcsaxes")
    and not name.startswith("astropy.visualization.mpl_")
    and "matplotlib" not in name,
)

datas = collect_data_files("astropy")
