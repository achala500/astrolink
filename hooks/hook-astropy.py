from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Exclude astropy.visualization because it unconditionally imports matplotlib,
# which is not a required dependency in this headless/desktop field stack.
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

datas = [
    item for item in collect_data_files("astropy")
    if "visualization" not in item[0]
]
