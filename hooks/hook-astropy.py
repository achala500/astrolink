from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization")
)

datas = [
    d for d in collect_data_files("astropy")
    if "visualization" not in d[0] and "visualization" not in d[1]
]

excludedimports = [
    "matplotlib",
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]
