from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization as it requires matplotlib (which is excluded)
hiddenimports = collect_submodules("astropy", filter=lambda name: "astropy.visualization" not in name)
