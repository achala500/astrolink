from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization to prevent PyInstaller from importing wcsaxes (which requires matplotlib)
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
