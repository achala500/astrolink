from PyInstaller.utils.hooks import collect_submodules

excludedimports = [
    "matplotlib",
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

# Exclude astropy.visualization submodules because wcsaxes requires matplotlib
hiddenimports = collect_submodules("astropy", filter=lambda name: not name.startswith("astropy.visualization"))
