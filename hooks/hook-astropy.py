from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Exclude astropy.visualization submodules and data files because wcsaxes requires matplotlib,
# which is intentionally excluded from standalone desktop builds.
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
datas = [
    d for d in collect_data_files("astropy")
    if "visualization" not in d[0] and "visualization" not in d[1]
]
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
    "matplotlib",
]
