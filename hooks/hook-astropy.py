from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Exclude astropy.visualization.wcsaxes during submodule collection
# to prevent pytest.importorskip("matplotlib") from raising Skipped when matplotlib is excluded
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: "visualization.wcsaxes" not in name,
    on_error="warn once",
)
datas = collect_data_files("astropy")
