from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Exclude visualization and wcsaxes submodules to prevent pytest.importorskip("matplotlib")
# from raising Skipped during PyInstaller find_binary_dependencies on Windows when matplotlib is excluded.
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
datas = collect_data_files(
    "astropy",
    excludes=["astropy/visualization/*", "astropy/visualization"],
)
excludedimports = ["astropy.visualization", "matplotlib"]
