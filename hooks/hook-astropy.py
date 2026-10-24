from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Exclude astropy.visualization to prevent matplotlib import attempt during PyInstaller module collection
datas = collect_data_files("astropy", excludes=["**/visualization/**", "**/visualization/*"])
hiddenimports = collect_submodules("astropy", filter=lambda name: "visualization" not in name)
excludedimports = ["matplotlib", "astropy.visualization"]
