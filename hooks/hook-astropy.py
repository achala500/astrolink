"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization and matplotlib to avoid Skipped/ImportErrors
when matplotlib is excluded from the build.
"""

excludedimports = ['matplotlib', 'astropy.visualization']
