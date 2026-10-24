from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization to prevent matplotlib import attempt during PyInstaller module collection
hiddenimports = collect_submodules("astropy", filter=lambda name: "visualization" not in name)
