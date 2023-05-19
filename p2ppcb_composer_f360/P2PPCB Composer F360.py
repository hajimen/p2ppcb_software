import sys
import os
import pathlib


CURRENT_DIR = pathlib.Path(os.path.dirname(__file__))
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))
from reimport import reimport
reimport(['p2ppcb_parts_resolver.resolver', 'f360_common', 'p2ppcb_parts_depot.depot',
          'route.route', 'p2ppcb_composer.cmd_common', 'p2ppcb_composer.cmd_key_common',
          'p2ppcb_composer.cmd_init_project', 'p2ppcb_composer.cmd_load_kle', 'p2ppcb_composer.cmd_matrix_route',
          'p2ppcb_composer.cmd_move_key', 'p2ppcb_composer.cmd_change_key', 'p2ppcb_composer.cmd_edit_frame',
          'p2ppcb_composer.cmd_set_attribute', 'p2ppcb_composer.cmd_remove_undercut', 'p2ppcb_composer.toolbar',
          'regex_selector.regex_selector'], ['mainboard'])
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
