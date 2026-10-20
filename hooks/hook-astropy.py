from PyInstaller.utils.hooks import collect_data_files, collect_submodules

excludedimports = [
    "matplotlib",
    "matplotlib.pyplot",
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

datas = collect_data_files("astropy", excludes=["**/visualization/**", "visualization/**"])
