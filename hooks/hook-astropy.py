from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization submodules to avoid matplotlib dependency during PyInstaller submodule collection
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
