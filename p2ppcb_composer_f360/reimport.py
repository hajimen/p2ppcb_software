import os
import sys
import importlib
import pathlib
import typing as ty
import platform
import adsk.core as ac


CURRENT_DIR = pathlib.Path(os.path.dirname(__file__))


def get_tag():
    ps = platform.system()
    if ps == 'Windows':
        return 'win_amd64'
    elif ps == 'Darwin':
        pm = platform.machine()
        if pm == 'x86_64':
            return 'macosx_10_10_x86_64'
        elif pm == 'arm64':
            return 'macosx_11_0_arm64'
    ac.Application.get().userInterface.messageBox('This platform is not available.')
    raise Exception()


ap = str(CURRENT_DIR / f'app-packages-{get_tag()}')
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
