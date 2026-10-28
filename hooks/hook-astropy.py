from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization submodules which trigger pytest.importorskip("matplotlib")
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
