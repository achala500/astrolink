from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Exclude astropy.visualization submodules because wcsaxes requires matplotlib,
# which is intentionally excluded from standalone desktop builds.
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
datas = collect_data_files("astropy")
