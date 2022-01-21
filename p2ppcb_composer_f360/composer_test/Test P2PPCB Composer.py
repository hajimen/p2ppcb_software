import sys
import os
import pathlib
import typing as ty
import unittest

import adsk.core as ac


CURRENT_DIR = pathlib.Path(os.path.dirname(__file__)).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from reimport import reimport

reimport(['p2ppcb_parts_resolver.resolver', 'f360_common', 'p2ppcb_parts_depot.depot',
          'composer_test.test_base', 'route.route', 'p2ppcb_composer.cmd_common', 'p2ppcb_composer.cmd_key_common',
          'p2ppcb_composer.cmd_start_project', 'p2ppcb_composer.cmd_load_kle', 'p2ppcb_composer.cmd_matrix_route',
          'p2ppcb_composer.cmd_move_key', 'p2ppcb_composer.cmd_change_key', 'p2ppcb_composer.cmd_edit_frame',
          'p2ppcb_composer.cmd_set_attribute', 'p2ppcb_composer.toolbar', 'composer_test.test_cmd', ], ['mainboard'])

from f360_common import catch_exception
from composer_test.test_base import HANDLERS, HANDLER_IDS

APP: ac.Application


def load_automated_tests(test_suite: unittest.TestSuite):
    from composer_test.test_cmd import TestCmdCommon
    test_suite.addTest(TestCmdCommon('test_check_key_placeholders'))
    test_suite.addTest(TestCmdCommon('test_check_layout_plane'))
    test_suite.addTest(TestCmdCommon('test_place_key_placeholders'))
    test_suite.addTest(TestCmdCommon('test_prepare_key_assembly'))
    test_suite.addTest(TestCmdCommon('test_check_intra_key_assembly_interference'))

    from composer_test.test_cmd import TestStartProject
    test_suite.addTest(TestStartProject('test_initialize'))

    from composer_test.test_cmd import TestLoadKle
    test_suite.addTest(TestLoadKle('test_place_locators'))

    from composer_test.test_cmd import TestMatrixRoute
    test_suite.addTest(TestMatrixRoute('test_generate_route'))
    test_suite.addTest(TestMatrixRoute('test_draw_wire'))
    test_suite.addTest(TestMatrixRoute('test_generate_keymap'))


def load_manual_tests(test_suite: unittest.TestSuite):
    '''
    These tests require manual image comparison.
    '''
    from composer_test.test_cmd import TestStartProject
    test_suite.addTest(TestStartProject('test_generate_scaffold'))

    from composer_test.test_cmd import TestMoveKey
    test_suite.addTest(TestMoveKey('test_cmd'))

    from composer_test.test_cmd import TestChangeKeyDescs
    test_suite.addTest(TestChangeKeyDescs('test_cmd'))

    from composer_test.test_cmd import TestEditFrame
    test_suite.addTest(TestEditFrame('test_generate_frame'))


def load_notorious_tests(test_suite: unittest.TestSuite):
    '''
    This test contains some side effects. You should restart F360 after this test.
    '''
    from composer_test.test_cmd import TestCmdCommon
    test_suite.addTest(TestCmdCommon('test_prepare_parts_sync'))


@catch_exception
def run(context):
    global APP
    APP = ac.Application.get()
    test_suite = unittest.TestSuite()

    load_automated_tests(test_suite)
    # load_manual_tests(test_suite)
    # load_notorious_tests(test_suite)

    # Run a command interactively

    # from composer_test.test_cmd import TestCmdCommon
    # test_suite.addTest(TestTestBase('test_cmd_interactive'))

    # from composer_test.test_cmd import TestStartProject
    # test_suite.addTest(TestStartProject('test_cmd_interactive'))

    # from composer_test.test_cmd import TestLoadKle
    # test_suite.addTest(TestLoadKle('test_cmd_interactive'))

    # from composer_test.test_cmd import TestMoveKey
    # test_suite.addTest(TestMoveKey('test_cmd_interactive'))

    # from composer_test.test_cmd import TestChangeKeyDescs
    # test_suite.addTest(TestChangeKeyDescs('test_cmd_interactive_change_key_descs'))
    # test_suite.addTest(TestChangeKeyDescs('test_cmd_interactive_check_key_assembly'))

    # from composer_test.test_cmd import TestMatrixRoute
    # test_suite.addTest(TestMatrixRoute('test_cmd_interactive_assign_matrix'))
    # test_suite.addTest(TestMatrixRoute('test_cmd_interactive_generate_route'))

    # from composer_test.test_cmd import TestEditFrame
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_generate_frame'))
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_place_mb'))
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_place_foot'))
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_finish'))

    # from composer_test.test_cmd import TestSetAttribute
    # test_suite.addTest(TestSetAttribute('test_cmd_interactive'))

    runner = unittest.TextTestRunner()
    runner.run(test_suite)


@catch_exception
def stop(context):
    ui = APP.userInterface

    # Cancel active command
    APP.executeTextCommand('NuCommands.CancelCmd')

    cmd_defs: ac.CommandDefinitions = ui.commandDefinitions
    for i in HANDLER_IDS:
        cmd_def: ty.Optional[ac.CommandDefinition] = cmd_defs.itemById(i)
        if cmd_def is not None:
            cmd_def.deleteMe()
            cmd_def = cmd_defs.itemById(i)
            if cmd_def is not None:
                print(f'{i} deleteMe() failed.')

    HANDLERS.clear()
    HANDLER_IDS.clear()
    print('stop')
