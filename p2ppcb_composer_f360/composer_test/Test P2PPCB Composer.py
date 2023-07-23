import sys
import os
import pathlib
import typing as ty
import unittest
import traceback
import importlib

import adsk
import adsk.core as ac


CURRENT_DIR = pathlib.Path(os.path.dirname(__file__)).parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

import reimport as _to_reload
importlib.reload(_to_reload)
from reimport import reimport

reimport(['p2ppcb_parts_resolver.resolver', 'f360_common', 'p2ppcb_parts_depot.depot',
          'route.route'], ['mainboard', 'composer_test', 'p2ppcb_composer'])

from composer_test.test_base import HANDLERS

APP: ac.Application


def catch_exception(func: ty.Callable):
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            adsk.terminate()
    return wrapped


def load_automated_tests(test_suite: unittest.TestSuite):
    from composer_test.test_utility import TestF360Common
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestF360Common))

    from composer_test.test_cmd import TestCmdCommon
    test_suite.addTest(TestCmdCommon('test_check_key_placeholders'))
    test_suite.addTest(TestCmdCommon('test_check_layout_plane'))
    test_suite.addTest(TestCmdCommon('test_place_key_placeholders'))
    test_suite.addTest(TestCmdCommon('test_prepare_key_assembly'))
    test_suite.addTest(TestCmdCommon('test_check_intra_key_assembly_interference'))
    test_suite.addTest(TestCmdCommon('test_prepare_parts_sync_exception'))

    from composer_test.test_cmd import TestInitProject
    test_suite.addTest(TestInitProject('test_initialize'))
    test_suite.addTest(TestInitProject('test_generate_scaffold'))

    from composer_test.test_cmd import TestLoadKle
    test_suite.addTest(TestLoadKle('test_place_locators'))

    from composer_test.test_cmd import TestMatrixRoute
    test_suite.addTest(TestMatrixRoute('test_generate_route'))
    test_suite.addTest(TestMatrixRoute('test_draw_wire'))
    test_suite.addTest(TestMatrixRoute('test_generate_keymap'))

    from composer_test.test_cmd import TestMoveKey
    test_suite.addTest(TestMoveKey('test_cmd'))

    from composer_test.test_cmd import TestChangeKeyDescs
    test_suite.addTest(TestChangeKeyDescs('test_cmd'))

    from composer_test.test_cmd import TestEditFrame
    test_suite.addTest(TestEditFrame('test_fill'))


def load_notorious_tests(test_suite: unittest.TestSuite):
    '''
    This test contains some side effects. You should restart F360 after this test.
    Manual operation is required.
    '''
    from composer_test.test_cmd import TestCmdCache
    # test_suite.addTest(TestCmdCache('test_prepare_parts_sync'))  # For regression testing, this is redundant.
    test_suite.addTest(TestCmdCache('test_cherry'))
    test_suite.addTest(TestCmdCache('test_choc_v1'))
    test_suite.addTest(TestCmdCache('test_dsa'))
    test_suite.addTest(TestCmdCache('test_junana'))
    test_suite.addTest(TestCmdCache('test_mx_oem'))
    test_suite.addTest(TestCmdCache('test_xda'))


@catch_exception
def run(context):
    global APP
    APP = ac.Application.get()
    test_suite = unittest.TestSuite()

    load_automated_tests(test_suite)
    # load_notorious_tests(test_suite)

    # Run a command interactively

    # from composer_test.test_cmd import TestInitProject
    # test_suite.addTest(TestInitProject('test_cmd_interactive'))

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
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_fill'))
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_place_mb'))
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_place_foot'))
    # test_suite.addTest(TestEditFrame('test_cmd_interactive_hole'))

    # from composer_test.test_cmd import TestSetAttribute
    # test_suite.addTest(TestSetAttribute('test_cmd_interactive'))

    # from composer_test.test_cmd import TestRegexSelector
    # test_suite.addTest(TestRegexSelector('test_cmd_interactive'))

    # from composer_test.test_cmd import TestRemoveUndercut
    # test_suite.addTest(TestRemoveUndercut('test_cmd_interactive'))

    runner = unittest.TextTestRunner()
    runner.run(test_suite)


@catch_exception
def stop(context):
    # Cancel active command
    APP.executeTextCommand('NuCommands.CancelCmd')
    HANDLERS.clear()
    print('stop')
