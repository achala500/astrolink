from PyInstaller.utils.hooks import collect_submodules

# Collect astropy submodules, filtering out astropy.visualization which requires matplotlib
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)

# Exclude astropy.visualization explicitly so PyInstaller's binary dependency analysis does not import it
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]
