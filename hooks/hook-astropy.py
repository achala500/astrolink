from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules("astropy", filter=lambda name: not name.startswith("astropy.visualization"))
