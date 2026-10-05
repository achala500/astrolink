from PyInstaller.utils.hooks import collect_submodules

# Collect astropy.io.fits submodules needed for FITS ingestion, excluding visualization/tests
hiddenimports = collect_submodules(
    "astropy.io.fits",
    filter=lambda name: "tests" not in name,
)
