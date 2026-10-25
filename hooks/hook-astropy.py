from PyInstaller.utils.hooks import collect_submodules

# Collect astropy submodules except astropy.visualization which requires matplotlib
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization")
)
