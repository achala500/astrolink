from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization submodules which require optional matplotlib dependency
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization")
)
