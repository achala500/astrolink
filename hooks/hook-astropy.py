"""PyInstaller custom hook for astropy.

Astropy's visualization subpackage imports matplotlib, which fails when matplotlib
is excluded in astrolink.spec. Passing filter=lambda name: not name.startswith('astropy.visualization')
to collect_submodules ensures that astropy.visualization is skipped during submodule collection.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules(
    'astropy',
    filter=lambda name: not name.startswith('astropy.visualization')
)

excludedimports = ['astropy.visualization']
