from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "visualization" not in name,
)

datas = [
    (src, dest)
    for src, dest in collect_data_files("astropy")
    if "visualization" not in src and "visualization" not in dest
]
