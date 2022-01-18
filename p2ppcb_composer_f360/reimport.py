import os
import sys
import importlib
import pathlib
import typing as ty


CURRENT_DIR = pathlib.Path(os.path.dirname(__file__))
ap = str(CURRENT_DIR / 'app-packages')
if ap not in sys.path:
    sys.path.append(ap)
del ap


def reimport(module_names: ty.List[str], package_names: ty.List[str] = []):
    importlib.invalidate_caches()
    for i in module_names:
        if i in sys.modules:
            importlib.reload(sys.modules[i])
    for i in package_names:
        for ii in list(sys.modules.keys()):
            if ii.startswith(i):
                importlib.reload(sys.modules[ii])
