from PyInstaller.utils.hooks import collect_submodules

# Exclude astropy.visualization modules to prevent pytest.importorskip("matplotlib") failure
excludedimports = [
    "astropy.visualization",
    "astropy.visualization.wcsaxes",
]

hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
)
