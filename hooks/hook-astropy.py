"""Custom PyInstaller hook for astropy.

Excludes astropy.visualization (which attempts to import optional matplotlib
and raises pytest.skip during module import) when collecting submodules for astropy.
"""

from __future__ import annotations

import importlib
import pkgutil
import astropy

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('astropy')


def _walk_astropy_submodules(path, prefix=''):
    for info in pkgutil.iter_modules(path, prefix):
        if info.name.startswith('astropy.visualization'):
            continue
        yield info.name
        if info.ispkg:
            try:
                subpkg = importlib.import_module(info.name)
                if hasattr(subpkg, '__path__'):
                    yield from _walk_astropy_submodules(subpkg.__path__, info.name + '.')
            except Exception:
                pass


hiddenimports = ['astropy'] + list(_walk_astropy_submodules(astropy.__path__, 'astropy.'))
excludedimports = ['astropy.visualization', 'matplotlib']
