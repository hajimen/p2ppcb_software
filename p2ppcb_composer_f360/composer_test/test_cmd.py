import os
import pathlib
import typing as ty
import pickle
import unittest

import adsk.core as ac
import adsk.fusion as af
import adsk

from f360_common import AN_HOLE, AN_MEV, AN_MF, CN_DEPOT_APPEARANCE, CN_DEPOT_KEY_ASSEMBLY, CN_DEPOT_PARTS, CN_FOOT, CN_INTERNAL, CN_KEY_LOCATORS, \
    CN_KEY_PLACEHOLDERS, CNP_PARTS, F3Occurrence, FourOrientation, SpecsOpsOnPn, SurrogateF3Occurrence, TwoOrientation, get_context, \
    get_part_info, key_placeholder_name, load_kle, reset_context
from p2ppcb_composer.cmd_common import AN_MAINBOARD, INP_ID_KEY_V_OFFSET_STR, INP_ID_ROTATION_AV, INP_ID_X_DV, INP_ID_Y_DV
from p2ppcb_composer.cmd_key_common import PP_KEY_ASSEMBLY_ON_SO, PrepareKeyPlaceholderParameter
from composer_test.test_base import execute_command, compare_image_by_eyes, capture_viewport, open_test_document, new_document, delete_document, do_many_events
from route.route import FlatCablePlacement


CURRENT_DIR = pathlib.Path(os.path.dirname(__file__)).parent
TEST_F3D_DIR = CURRENT_DIR / 'test_data/f3d'
TEST_KLE_DIR = CURRENT_DIR / 'test_data/kle'
TEST_PNG_DIR = CURRENT_DIR / 'test_data/png'
TEST_PKL_DIR = CURRENT_DIR / 'test_data/pkl'


class TestCmdCommon(unittest.TestCase):
    def test_check_key_placeholders(self):
        from p2ppcb_composer.cmd_common import _check_key_placeholders
        doc = open_test_document(TEST_F3D_DIR / 'check_key_placeholders.f3d')
        result = _check_key_placeholders({'125u 0_KP'}, {AN_HOLE: True, AN_MEV: True, AN_MF: True})
        if result is None:
            self.fail()
        else:
            hit_mev, hit_hole, hit_mf, hit_kpns, cache_temp_body = result
            self.assertEqual(len(hit_mev), 2)
            self.assertListEqual(hit_hole, [])
            self.assertListEqual(hit_mf, [])
            self.assertEqual(len(hit_kpns), 2)
            self.assertEqual(len(cache_temp_body), 20)
        doc.close(False)

    def test_check_layout_plane(self):
        from p2ppcb_composer.cmd_common import check_layout_plane
        doc = new_document()
        con = reset_context()
        yz_sk = con.root_comp.sketches.add(con.root_comp.yZConstructionPlane)
        sp = yz_sk.sketchPoints
        planes = con.root_comp.constructionPlanes
        cp_in = planes.createInput()
        right_points = [
            ac.Point3D.create(-15., -4. - 1.4, 5.),
            ac.Point3D.create(1., -4. - 1.4, 5.),
            ac.Point3D.create(0., 7. - 1.4, 5.5)
        ]
        cp_in.setByThreePoints(
            sp.add(right_points[0]),
            sp.add(right_points[1]),
            sp.add(right_points[2]))
        right_cp = planes.add(cp_in)
        right_plane = check_layout_plane(right_cp)
        self.assertIsNone(right_plane.intersectWithLine(ac.Line3D.create(right_points[0], right_points[1]).asInfiniteLine()))
        self.assertIsNone(right_plane.intersectWithLine(ac.Line3D.create(right_points[1], right_points[2]).asInfiniteLine()))
        cp_in2 = planes.createInput()
        bad_points = [
            ac.Point3D.create(0., 0., 0.),
            ac.Point3D.create(0., 0., 1.),
            ac.Point3D.create(0., 1., 1.)
        ]
        cp_in2.setByThreePoints(
            sp.add(bad_points[0]),
            sp.add(bad_points[1]),
            sp.add(bad_points[2]))
        bad_cp = planes.add(cp_in2)

        with self.assertRaises(Exception):
            _ = check_layout_plane(bad_cp)

        doc.close(False)

    def test_place_key_placeholders(self):
        from p2ppcb_composer.cmd_key_common import place_key_placeholders
        doc = open_test_document(TEST_F3D_DIR / 'place_key_placeholders.f3d')
        con = get_context()
        place_key_placeholders()
        inl_occ = con.child[CN_INTERNAL]
        key_placeholders_occ = inl_occ.child[CN_KEY_PLACEHOLDERS]
        self.assertIsInstance(key_placeholders_occ.child['1u 5_KP'], SurrogateF3Occurrence)
        self.assertEqual(con.prepare_parameter_dict[PP_KEY_ASSEMBLY_ON_SO]['1u DSA Cherry-style plate mount Front Choc V2 Front StemBottom'].kps[5].legend[9], 'KC_DELETE')
        doc.close(False)

    def test_prepare_key_assembly(self):
        import p2ppcb_parts_resolver.resolver as parts_resolver
        from p2ppcb_composer.cmd_key_common import prepare_key_assembly, PrepareKeyAssemblyParameter, PP_SURROGATE_KEY_ASSEMBLY_NAMES
        doc = open_test_document(TEST_F3D_DIR / 'after_init.f3d')
        con = get_context()
        inl_occ = con.child[CN_INTERNAL]
        key_placeholders_occ = inl_occ.child.new_real(CN_KEY_PLACEHOLDERS)
        key_placeholders_occ.child.new_surrogate(key_placeholder_name(0, '1u'))

        pp_ka_on_so: ty.Dict[str, 'PrepareKeyAssemblyParameter'] = {}
        pp_ka_on_so['_'] = PrepareKeyAssemblyParameter(
            '1u', '1u', 'DSA', 'Cherry-style plate mount', TwoOrientation.Front, 'Choc V2', FourOrientation.Front, parts_resolver.AlignTo.StemBottom, 0.,
            [
                PrepareKeyPlaceholderParameter(0, [''] * 12)
            ]
        )
        con.prepare_parameter_dict[PP_KEY_ASSEMBLY_ON_SO] = pp_ka_on_so
        con.prepare_parameter_dict[PP_SURROGATE_KEY_ASSEMBLY_NAMES] = {}
        specs_ops_on_pn: SpecsOpsOnPn = {}
        specs_ops_on_pn['1u'] = [('1u', parts_resolver.OccurrenceParameter(
            (0., 0.), (0., 0.), (1., 1.), 0., [''] * 12, CURRENT_DIR, 0
        ))]
        pps_part = prepare_key_assembly(specs_ops_on_pn, get_part_info())
        self.assertEqual(pps_part[0].new_name, 'Cap DSA 1u Travel 3.2 millimeter_P')
        self.assertEqual(pps_part[1].new_name, 'Switch Choc V2_P')
        self.assertEqual(pps_part[2].new_name, 'PCB Choc V2_P')
        doc.close(False)

    def test_check_intra_key_assembly_interference(self):
        # # Make test data.
        # cache_docname = 'Test check_intra_key_assembly_interference Cache'
        # test_docname = 'test_check_intra_key_assembly_interference'
        # from p2ppcb_composer.cmd_key_common import place_key_placeholders, prepare_key_assembly, prepare_parts_sync
        # from p2ppcb_composer.cmd_load_kle import place_locators

        # doc = open_test_document(TEST_F3D_DIR / 'after_init.f3d')
        # con = get_context()
        # pi = get_part_info()
        # place_locators_args = load_kle(TEST_KLE_DIR / 'check_intra_key_assembly_interference.json', pi)
        # place_locators(pi, *place_locators_args)
        # place_key_placeholders()
        # specs_ops_on_pn, _, _ = place_locators_args
        # pps_part = prepare_key_assembly(specs_ops_on_pn, pi)
        # admin_folder: ac.DataFolder = con.app.data.dataProjects[0].rootFolder
        # doc.saveAs(test_docname, admin_folder, 'Test prepare_parts_sync', '')
        # prepare_parts_sync(pps_part, cache_docname)

        from p2ppcb_composer.cmd_key_common import _check_intra_key_assembly_interference
        doc = open_test_document(TEST_F3D_DIR / 'check_intra_key_assembly_interference.f3d')
        con = get_context()
        inl_occ = con.child[CN_INTERNAL]
        ka_occ_list = list(inl_occ.child[CN_DEPOT_KEY_ASSEMBLY].child.values())
        error_messages = _check_intra_key_assembly_interference(ka_occ_list)
        self.assertTrue(error_messages[0].startswith('Key Assembly DSA Cherry-style plate mount Front Choc V2 Front StemBottom 2u_KA has interference between its parts. You should avoid the combination of the parts.'))
        doc.close(False)

    def test_prepare_parts_sync(self):
        cache_docname = 'Test prepare_parts_sync Cache'
        test_docname = 'test_prepare_parts_sync'
        from p2ppcb_composer.cmd_key_common import place_key_placeholders, prepare_key_assembly, prepare_parts_sync
        from p2ppcb_composer.cmd_load_kle import place_locators

        doc = open_test_document(TEST_F3D_DIR / 'cache_prepare_parts_sync.f3d')
        con = get_context()
        admin_folder: ac.DataFolder = con.app.data.dataProjects[0].rootFolder
        doc.saveAs(cache_docname, admin_folder, 'Test Cache', '')
        doc.close(False)

        doc = open_test_document(TEST_F3D_DIR / 'after_init.f3d')
        con = get_context()
        pi = get_part_info()
        place_locators_args = load_kle(TEST_KLE_DIR / 'prepare_parts_sync.json', pi)
        place_locators(pi, *place_locators_args)
        place_key_placeholders()
        specs_ops_on_pn, _, _ = place_locators_args
        pps_part = prepare_key_assembly(specs_ops_on_pn, pi)
        with self.assertRaises(Exception):  # Exception: Start from a saved document.
            prepare_parts_sync(pps_part, cache_docname)
        admin_folder: ac.DataFolder = con.app.data.dataProjects[0].rootFolder
        doc.saveAs(test_docname, admin_folder, 'Test prepare_parts_sync', '')
        prepare_parts_sync(pps_part, cache_docname)
        img = capture_viewport()
        # img.save(TEST_PNG_DIR / 'prepare_parts_sync.png')
        self.assertTrue(compare_image_by_eyes(img, TEST_PNG_DIR / 'prepare_parts_sync.png'))
        doc.close(False)

        delete_document(test_docname)
        delete_document(cache_docname)


class TestInitProject(unittest.TestCase):
    def test_cmd_interactive(self):
        from p2ppcb_composer.cmd_init_project import InitializeP2ppcbProjectCommandHandler
        execute_command(InitializeP2ppcbProjectCommandHandler)
        adsk.autoTerminate(False)
    
    def test_initialize(self):
        doc = new_document()
        con = reset_context()
        from p2ppcb_composer.cmd_init_project import initialize
        inl_occ = con.child.get_real(CN_INTERNAL)
        inl_occ.comp_attr[AN_MAINBOARD] = 'Alice'
        initialize()
        self.assertTrue(CN_INTERNAL in con.child)
        self.assertIsInstance(inl_occ, F3Occurrence)
        self.assertTrue(CN_DEPOT_APPEARANCE in inl_occ.child)
        depot_appearance_occ = inl_occ.child[CN_DEPOT_APPEARANCE]
        self.assertFalse(depot_appearance_occ.light_bulb)
        self.assertGreater(len(depot_appearance_occ.comp.bRepBodies), 0)
        self.assertTrue(CN_DEPOT_PARTS in inl_occ.child)
        depot_parts_occ = inl_occ.child[CN_DEPOT_PARTS]
        cn_mainboard_alice = 'Alice' + CNP_PARTS
        self.assertTrue(cn_mainboard_alice in depot_parts_occ.child)
        alice_occ = depot_parts_occ.child[cn_mainboard_alice]
        self.assertGreater(len(alice_occ.comp.bRepBodies), 0)
        self.assertTrue(CN_FOOT in depot_parts_occ.child)
        foot_occ = depot_parts_occ.child[CN_FOOT]
        self.assertGreater(len(foot_occ.comp.bRepBodies), 0)
        self.assertFalse(depot_parts_occ.light_bulb)
        self.assertTrue(con.des.designType == af.DesignTypes.DirectDesignType)
        doc.close(False)

    def test_generate_scaffold(self):
        doc = new_document()
        from p2ppcb_composer.cmd_init_project import generate_scaffold
        pitch_x, pitch_y, offset, skeleton_surface, alternative_surface, layout_plane = generate_scaffold()
        self.assertEqual(pitch_x, 1.9)
        self.assertEqual(pitch_y, 1.9)
        self.assertEqual(offset, 0.)
        self.assertIsInstance(skeleton_surface, af.BRepBody)
        self.assertIsInstance(alternative_surface, af.BRepBody)
        self.assertIsInstance(layout_plane, af.ConstructionPlane)
        img = capture_viewport()
        # img.save(CURRENT_DIR / 'test_data/generate_scaffold.png')
        doc.close(False)
        self.assertTrue(compare_image_by_eyes(img, TEST_PNG_DIR / 'generate_scaffold.png'))


class TestLoadKle(unittest.TestCase):
    def test_place_locators(self):
        import p2ppcb_parts_depot.depot as parts_depot
        from p2ppcb_composer.cmd_key_common import PP_KEY_LOCATORS_ON_SPECIFIER
        from p2ppcb_composer.cmd_load_kle import place_locators
        doc = open_test_document(TEST_F3D_DIR / 'after_init.f3d')
        con = get_context()
        pi = get_part_info()
        # # Make test data.
        # place_locators_args = load_kle(TEST_KLE_DIR / 'prepare_parts_sync.json', pi)
        # with open(TEST_PKL_DIR / 'place_locators.pkl', 'wb') as f:
        #     pickle.dump(place_locators_args, f)
        with open(TEST_PKL_DIR / 'place_locators.pkl', 'rb') as f:
            place_locators_args = pickle.load(f)
        place_locators(pi, *place_locators_args)
        key_locators_occ = con.child[CN_INTERNAL].child[CN_KEY_LOCATORS]
        o = key_locators_occ.child['1u 0_KL']
        for v1, v2 in zip(o.transform.asArray(), [
                1.0, 0.0, 0.0, 0.0,
                0.0, 0.9989685402102997, -0.045407660918649985, 0.0,
                0.0, 0.045407660918649985, 0.9989685402102997, 5.245454545454545,
                0.0, 0.0, 0.0, 1.0]):
            self.assertAlmostEqual(v1, v2)
        pp_kl_on_specifier: ty.Dict[str, parts_depot.PrepareKeyLocatorParameter] = con.prepare_parameter_dict[PP_KEY_LOCATORS_ON_SPECIFIER]
        self.assertIsInstance(pp_kl_on_specifier['1u'], parts_depot.PrepareKeyLocatorParameter)
        doc.close(False)

    def test_cmd_interactive(self):
        from p2ppcb_composer.cmd_load_kle import LoadKleFileCommandHandler
        execute_command(LoadKleFileCommandHandler)
        adsk.autoTerminate(False)


# cspell: disable-next-line
MOVE_KEY_CHANGE_KEY_DESC_OCC_ONK = r'Commands.Select ONK::CmpInst=Untitled/Cmp=Untitled/CmpInsts/CmpInst=P2PPCB%20Internal%3A1/Cmp=P2PPCB%20Internal/CmpInsts/CmpInst=Key%20Locators%20mU0jU%3A1/Cmp=Key%20Locators%20mU0jU/CmpInsts/CmpInst=125u%200_KL%3A1'


class TestMoveKey(unittest.TestCase):
    def test_cmd_interactive(self):
        from p2ppcb_composer.cmd_move_key import MoveKeyCommandHandler
        execute_command(MoveKeyCommandHandler)
        adsk.autoTerminate(False)

    def test_cmd(self):
        from p2ppcb_composer.cmd_move_key import MoveKeyCommandHandler
        doc = open_test_document(TEST_F3D_DIR / 'move_key_change_key_descs.f3d')
        con = get_context()
        execute_command(MoveKeyCommandHandler)
        do_many_events()
        con.app.executeTextCommand(MOVE_KEY_CHANGE_KEY_DESC_OCC_ONK)
        do_many_events()
        con.app.executeTextCommand(f'Commands.SetDouble {INP_ID_ROTATION_AV} {(90 / 360) * 2 * 3.141592}')
        con.app.executeTextCommand(f'Commands.SetDouble {INP_ID_X_DV} 0.5')
        con.app.executeTextCommand(f'Commands.SetDouble {INP_ID_Y_DV} 0.5')
        con.app.executeTextCommand('NuCommands.CommitCmd')
        adsk.doEvents()
        img = capture_viewport()
        # img.save(CURRENT_DIR / 'test_data/move_key.png')
        doc.close(False)
        self.assertTrue(compare_image_by_eyes(img, TEST_PNG_DIR / 'move_key.png'))


class TestChangeKeyDescs(unittest.TestCase):
    def test_cmd_interactive_change_key_descs(self):
        from p2ppcb_composer.cmd_change_key import ChangeKeyDescsCommandHandler
        execute_command(ChangeKeyDescsCommandHandler)
        adsk.autoTerminate(False)

    def test_cmd_interactive_check_key_assembly(self):
        from p2ppcb_composer.cmd_change_key import CheckKeyAssemblyCommandHandler
        execute_command(CheckKeyAssemblyCommandHandler)
        adsk.autoTerminate(False)

    def test_cmd(self):
        from p2ppcb_composer.cmd_change_key import ChangeKeyDescsCommandHandler
        doc = open_test_document(TEST_F3D_DIR / 'move_key_change_key_descs.f3d')
        con = get_context()
        execute_command(ChangeKeyDescsCommandHandler)
        do_many_events()
        con.app.executeTextCommand(MOVE_KEY_CHANGE_KEY_DESC_OCC_ONK)
        do_many_events()
        con.app.executeTextCommand(f'Commands.SetString {INP_ID_KEY_V_OFFSET_STR} "5 mm"')
        con.app.executeTextCommand('NuCommands.CommitCmd')
        adsk.doEvents()
        img = capture_viewport()
        # img.save(CURRENT_DIR / 'test_data/change_key.png')
        doc.close(False)
        self.assertTrue(compare_image_by_eyes(img, TEST_PNG_DIR / 'change_key.png'))


class TestMatrixRoute(unittest.TestCase):
    def test_cmd_interactive_assign_matrix(self):
        from p2ppcb_composer.cmd_matrix_route import AssignMatrixCommandHandler
        execute_command(AssignMatrixCommandHandler)
        adsk.autoTerminate(False)

    def test_cmd_interactive_generate_route(self):
        from p2ppcb_composer.cmd_matrix_route import GenerateRouteCommandHandler
        execute_command(GenerateRouteCommandHandler)
        adsk.autoTerminate(False)

    def test_generate_route(self):
        import numpy as np
        from route import route as rt
        from mainboard.Alice import constants
        doc = open_test_document(TEST_F3D_DIR / 'matrix_route.f3d')
        mc = constants()

        # from collections import defaultdict
        # from f360_common import BadConditionException, AN_COL_NAME, AN_ROW_NAME
        # inl_occ = get_context().child[CN_INTERNAL]
        # matrix: ty.Dict[str, ty.Dict[str, str]] = defaultdict(lambda: defaultdict(str))
        # for kl_occ in inl_occ.child[CN_KEY_LOCATORS].child.values():
        #     if AN_ROW_NAME in kl_occ.comp_attr and AN_COL_NAME in kl_occ.comp_attr:
        #         matrix[kl_occ.comp_attr[AN_ROW_NAME]][kl_occ.comp_attr[AN_COL_NAME]] = kl_occ.name
        #     else:
        #         raise BadConditionException('Assign S/D to all key locators.')
        # with open((TEST_PKL_DIR / 'matrix.pkl'), 'wb') as f:
        #     pickle.dump({k: dict(v) for k, v in matrix.items()}, f)

        with open(TEST_PKL_DIR / 'matrix.pkl', 'rb') as f:
            matrix = pickle.load(f)
        flat_cable_placements: ty.List[rt.FlatCablePlacement] = []
        flat_cable_placements.append(FlatCablePlacement((4., 0.), np.pi / 2, mc.flat_cables[0]))
        flat_cable_placements.append(FlatCablePlacement((0., 6.), 0., mc.flat_cables[1]))
        result = rt.generate_route(matrix, flat_cable_placements)
        # with open(TEST_PKL_DIR / 'route.pkl', 'wb') as f:
        #     pickle.dump(result, f)
        with open(TEST_PKL_DIR / 'route.pkl', 'rb') as f:
            oracle = pickle.load(f)
            self.assertTrue(oracle == result)
        doc.close(False)

    def test_draw_wire(self):
        from PIL import Image, ImageChops
        from route import route as rt
        with open(TEST_PKL_DIR / 'route.pkl', 'rb') as f:
            route = pickle.load(f)
        img_row, img_col = rt.draw_wire(*route)
        # img_row.save(str(TEST_PNG_DIR / 'draw_wire_row.png'))
        # img_col.save(str(TEST_PNG_DIR / 'draw_wire_col.png'))
        for rc, img in zip(['row', 'col'], [img_row, img_col]):
            oracle = Image.open(str(TEST_PNG_DIR / f'draw_wire_{rc}.png'))
            self.assertIsNone(ImageChops.difference(img, oracle).getbbox())

    def test_generate_keymap(self):
        from route import route as rt
        from mainboard.Alice import constants
        with open(TEST_PKL_DIR / 'route.pkl', 'rb') as f:
            keys_rc, _, _ = pickle.load(f)
        doc = open_test_document(TEST_F3D_DIR / 'matrix_route.f3d')
        mbc = constants()
        generated_snippet, via_json = rt.generate_keymap(keys_rc, mbc)
        # with open((TEST_PKL_DIR / 'keymap.pkl'), 'wb') as f:
        #     pickle.dump((generated_snippet, via_json), f)
        with open((TEST_PKL_DIR / 'keymap.pkl'), 'rb') as f:
            oracle_snippet, oracle_via = pickle.load(f)
        self.assertEqual(generated_snippet, oracle_snippet)
        self.assertEqual(via_json, oracle_via)
        doc.close(False)


class TestEditFrame(unittest.TestCase):
    def test_cmd_interactive_fill(self):
        from p2ppcb_composer.cmd_edit_frame import FillFrameCommandHandler
        execute_command(FillFrameCommandHandler)
        adsk.autoTerminate(False)

    def test_cmd_interactive_place_mb(self):
        from p2ppcb_composer.cmd_edit_frame import PlaceMainboardCommandHandler
        execute_command(PlaceMainboardCommandHandler)
        adsk.autoTerminate(False)

    def test_cmd_interactive_place_foot(self):
        from p2ppcb_composer.cmd_edit_frame import PlaceFootCommandHandler
        execute_command(PlaceFootCommandHandler)
        adsk.autoTerminate(False)

    def test_cmd_interactive_hole(self):
        from p2ppcb_composer.cmd_edit_frame import HolePartsCommandHandler
        execute_command(HolePartsCommandHandler)
        adsk.autoTerminate(False)

    def test_fill(self):
        from p2ppcb_composer.cmd_edit_frame import fill_frame
        doc = open_test_document(TEST_F3D_DIR / 'fill_frame.f3d')
        con = get_context()
        before_frame_bodies = [b for b in con.comp.bRepBodies if b.isSolid]
        profs = [p for p in con.comp.sketches[1].profiles]
        fill_frame(True, profs, before_frame_bodies, 0.8)
        con.child[CN_INTERNAL].light_bulb = False
        img = capture_viewport()
        # img.save(TEST_PNG_DIR / 'fill_frame.png')
        self.assertTrue(compare_image_by_eyes(img, TEST_PNG_DIR / 'fill_frame.png'))
        doc.close(False)


class TestSetAttribute(unittest.TestCase):
    def test_cmd_interactive(self):
        from p2ppcb_composer.cmd_set_attribute import SetAttributeCommandHandler
        execute_command(SetAttributeCommandHandler)
        adsk.autoTerminate(False)
