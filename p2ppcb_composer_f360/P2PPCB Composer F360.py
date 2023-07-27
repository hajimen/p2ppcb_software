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
    print('Run P2PPCB Composer F360')
    init_toolbar()


@catch_exception
def stop(context):
    terminate_toolbar()
    print('Stop P2PPCB Composer F360')
