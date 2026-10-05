from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = [
    "matplotlib",
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
    "astropy.visualization.mpl_normalize",
    "astropy.visualization.mpl_style",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization")
    and "matplotlib" not in name,
)

datas = collect_data_files("astropy")
