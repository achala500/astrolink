# Custom PyInstaller hook for astropy
# Excludes astropy.visualization to prevent matplotlib import dependency errors during PyInstaller analysis

excludedimports = ['astropy.visualization', 'astropy.visualization.wcsaxes']
