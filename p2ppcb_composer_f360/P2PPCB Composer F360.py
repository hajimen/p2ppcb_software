import sys
import os
import pathlib


CURRENT_DIR = pathlib.Path(os.path.dirname(__file__))
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))
from reimport import reimport
reimport(['p2ppcb_parts_resolver.resolver', 'f360_common', 'p2ppcb_parts_depot.depot',
          'route.route'], ['mainboard', 'p2ppcb_composer'])
from f360_common import catch_exception
from p2ppcb_composer.toolbar import init_toolbar, terminate_toolbar


@catch_exception
def run(context):
    import adsk.core as ac
    import adsk.fusion as af
    print('Run P2PPCB Composer F360')
    app = ac.Application.get()
    _fp = app.preferences.productPreferences.itemByName('Design')
    if _fp is None:
        print("ERROR: app.preferences.productPreferences.itemByName('Design') is None")
        raise Exception("app.preferences.productPreferences.itemByName('Design') is None")
    fp = af.FusionProductPreferences.cast(_fp)
    if fp.isFirstComponentGroundToParent:
        ui = app.userInterface
        r = ui.messageBox(
                'P2PPCB requires "First component grounded to parent" preference to be disabled, but it is now enabled. Change the preference? If you need to make it enabled, see General -> Design of the Preferences.',
                'P2PPCB',
                ac.MessageBoxButtonTypes.OKCancelButtonType)
        if r != ac.DialogResults.DialogOK:
            return
        fp.isFirstComponentGroundToParent = False
    init_toolbar()


@catch_exception
def stop(context):
    terminate_toolbar()
    print('Stop P2PPCB Composer F360')
