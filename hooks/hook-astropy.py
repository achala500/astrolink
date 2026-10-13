from PyInstaller.utils.hooks import collect_submodules

# Filter out astropy.visualization to prevent wcsaxes from triggering pytest.importorskip("matplotlib")
# when matplotlib is excluded or not installed.
hiddenimports = collect_submodules(
    "astropy",
    filter=lambda name: not name.startswith("astropy.visualization"),
    on_error="ignore"
)
