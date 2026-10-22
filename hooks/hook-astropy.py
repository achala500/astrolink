from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization to prevent matplotlib importorskip error when matplotlib is excluded
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization")
)
excludedimports = ["astropy.visualization", "matplotlib"]
