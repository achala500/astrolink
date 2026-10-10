from PyInstaller.utils.hooks import collect_submodules

# Filter out astropy.visualization which requires matplotlib (not installed / excluded)
hiddenimports = collect_submodules("astropy", filter=lambda name: "visualization" not in name)
