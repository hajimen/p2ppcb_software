import typing as ty
import pickle
import pathlib
import zlib
import base64
import numpy as np
from pint import Quantity
import p2ppcb_parts_resolver.resolver as parts_resolver
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput
from f360_common import AN_KEY_V_OFFSET, AN_LOCATORS_ENABLED, AN_LOCATORS_I, \
    AN_LOCATORS_LEGEND_PICKLED, AN_LOCATORS_PATTERN_NAME, AN_LOCATORS_SPECIFIER, ANS_OPTION, \
    CN_KEY_PLACEHOLDERS, DECAL_DESC_KEY_LOCATOR, BadConditionException, SpecsOpsOnPn, \
    VirtualF3Occurrence, CURRENT_DIR, get_context, CN_INTERNAL, CN_KEY_LOCATORS, key_locator_name, \
    ANS_KEY_PITCH, AN_KLE_B64, load_kle, get_part_info
import p2ppcb_parts_depot.depot as parts_depot
from p2ppcb_composer.cmd_common import AN_MAIN_SURFACE, get_ci, AN_LOCATORS_PLANE_TOKEN, MoveComponentCommandBlock, \
    CommandHandlerBase, AN_MAIN_KEY_V_OFFSET, AN_MAIN_LAYOUT_PLANE, ANS_MAIN_OPTION
from p2ppcb_composer.cmd_key_common import AN_LOCATORS_SKELETON_TOKEN, place_key_placeholders, prepare_key_assembly, prepare_parts_sync, get_layout_plane_transform, \
    INP_ID_LAYOUT_PLANE_SEL, AN_LOCATORS_ANGLE_TOKEN, PP_KEY_LOCATORS_ON_SPECIFIER


def place_locators(pi: parts_resolver.PartsInfo, specs_ops_on_pn: SpecsOpsOnPn, min_xyu, max_xyu):
    con = get_context()
    inl_occ = con.child[CN_INTERNAL]

    pp_kl_on_specifier: ty.Dict[str, parts_depot.PrepareKeyLocatorParameter] = con.prepare_parameter_dict[PP_KEY_LOCATORS_ON_SPECIFIER]
    main_surface = af.BRepBody.cast(con.attr_singleton[AN_MAIN_SURFACE][1])
    lp = af.ConstructionPlane.cast(con.attr_singleton[AN_MAIN_LAYOUT_PLANE][1])
    lp_trans = get_layout_plane_transform(lp)
    options = [inl_occ.comp_attr[an] for an in ANS_MAIN_OPTION]
    offset_str = inl_occ.comp_attr[AN_MAIN_KEY_V_OFFSET]

    locators_occ = con.child[CN_INTERNAL].child.get_real(CN_KEY_LOCATORS)
    locators_occ.light_bulb = True
    key_pitch_wd = {an: ty.cast(Quantity, Quantity(float(inl_occ.comp_attr[an]), 'cm')) for an in ANS_KEY_PITCH}
    u_wd = np.array([float(inl_occ.comp_attr[an]) for an in ANS_KEY_PITCH])
    min_xyu = np.array(min_xyu)
    max_xyu = np.array(max_xyu)
    w, h = (max_xyu - min_xyu) * u_wd  # type: ignore
    for pattern_name, specs_ops in specs_ops_on_pn.items():
        for i, (specifier, op) in enumerate(specs_ops):
            if op is None:
                continue
            name = key_locator_name(i, pattern_name)
            legend_pickled = pickle.dumps(op.legend).hex()

            def _on_surrogate(o: VirtualF3Occurrence):
                o.comp_attr[AN_LOCATORS_LEGEND_PICKLED] = legend_pickled
                o.comp_attr[AN_LOCATORS_SPECIFIER] = specifier
                o.comp_attr[AN_LOCATORS_PATTERN_NAME] = pattern_name
                o.comp_attr[AN_LOCATORS_I] = str(i)
                o.comp_attr[AN_LOCATORS_ENABLED] = 'True'
                for d, an in zip(options, ANS_OPTION):
                    o.comp_attr[an] = d
                o.comp_attr[AN_KEY_V_OFFSET] = offset_str
                o.comp_attr[AN_LOCATORS_SKELETON_TOKEN] = main_surface.entityToken
                o.comp_attr[AN_LOCATORS_ANGLE_TOKEN] = main_surface.entityToken
                o.comp_attr[AN_LOCATORS_PLANE_TOKEN] = lp.entityToken

                if specifier in pp_kl_on_specifier:
                    pp = pp_kl_on_specifier[specifier]
                else:
                    locator_decal_parameters = pi.resolve_decal(specifier, DECAL_DESC_KEY_LOCATOR)
                    pp = parts_depot.PrepareKeyLocatorParameter(
                        locator_decal_parameters,
                        parts_resolver.KEY_AREA_PATTERN_DIC[pattern_name],
                        key_pitch_wd,
                        []
                    )
                    pp_kl_on_specifier[specifier] = pp
                for n, _ in pp.names_images:
                    if n == name:
                        return
                pp.names_images.append(
                    (name, op.image_file_path)  # type: ignore
                )

            occ = locators_occ.child.get_virtual(name, on_surrogate=_on_surrogate)
            if occ.comp_attr[AN_LOCATORS_LEGEND_PICKLED] != legend_pickled:
                del locators_occ.child[name]
                occ = locators_occ.child.get_virtual(name, on_surrogate=_on_surrogate)
            r = - (op.angle * np.pi / 180)
            rot_mat = np.array([[np.cos(r), - np.sin(r)], [np.sin(r), np.cos(r)]])
            x, y = (np.array(op.center_xyu) - min_xyu) * u_wd  # type: ignore
            mat_3d = np.eye(4)
            mat_3d[:2, :2] = rot_mat
            mat_3d[:2, 3] = x - w / 2, h / 2 - y
            t = ac.Matrix3D.create()
            t.setWithArray(mat_3d.flatten().tolist())
            t.transformBy(lp_trans)
            occ.transform = t
            occ.light_bulb = True


class LoadKleFileCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.move_comp_cb: MoveComponentCommandBlock
        self.require_cn_key_locators = False

    @property
    def cmd_name(self) -> str:
        return 'Load KLE'

    @property
    def tooltip(self) -> str:
        return "Loads KLE's JSON file. It can require tens of minutes for large layouts, especially first time (cache file helps you after first time). You may see a dialog box which tells you the start/finish of RPA work (cache file helps). Cancel button of this command doesn't work as cancel."  # noqa

    @property
    def resource_folder(self) -> str:
        return 'Resources/load_kle'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()

        if not con.app.activeDocument.isSaved:
            raise BadConditionException('Save this document first.')

        file_dlg = con.ui.createFileDialog()
        file_dlg.isMultiSelectEnabled = False
        file_dlg.initialDirectory = str(CURRENT_DIR / 'scaffold_data')
        file_dlg.title = 'Open KLE file'
        file_dlg.filter = 'KLE File (*.json)'
        
        if file_dlg.showOpen() != ac.DialogResults.DialogOK:
            self.create_ok = False
            return
        kle_file_path = pathlib.Path(file_dlg.filename)
        with open(kle_file_path, 'rb') as f:
            kle_file_content = f.read()
        kle_b64 = base64.b64encode(zlib.compress(kle_file_content)).decode()
        if len(kle_b64.encode('utf-8')) > 2097152:
            raise BadConditionException('Sorry, the KLE file is too large.')
        inl_occ = con.child[CN_INTERNAL]
        inl_occ.comp_attr[AN_KLE_B64] = kle_b64

        pi = get_part_info()

        try:
            place_locators_args = load_kle(kle_file_path, pi)
        except Exception:
            raise BadConditionException('Internal Error: Please restart Fusion 360. If this error occurs again, something is corrupted.')

        place_locators(pi, *place_locators_args)

        place_key_placeholders()
        specs_ops_on_pn, _, _ = place_locators_args
        try:
            pps_part = prepare_key_assembly(specs_ops_on_pn, pi)
        except parts_resolver.SpecifierException as e:
            raise BadConditionException(f'Specifier "{e.missed_specifier}" is not available.\nAvailable specifiers:\n' + '\n'.join(e.available_specifiers))

        if len(pps_part) > 0:
            success = prepare_parts_sync(pps_part)
            if not success:
                raise BadConditionException('Internal Error: Please restart Fusion 360. If this error occurs again, something is corrupted.')

        self.move_comp_cb = MoveComponentCommandBlock(self)
        self.move_comp_cb.notify_create(event_args)

        lp = af.ConstructionPlane.cast(con.attr_singleton[AN_MAIN_LAYOUT_PLANE][1])
        t = get_layout_plane_transform(lp)
        if t is None:
            raise BadConditionException('The layout plane is invalid.')
        self.move_comp_cb.start_transaction(t)

        locators_occ = inl_occ.child.get_real(CN_KEY_LOCATORS)
        locators_occ.light_bulb = False
        key_placeholders_occ = inl_occ.child.get_real(CN_KEY_PLACEHOLDERS)
        key_placeholders_occ.light_bulb = False

    def get_selection_in(self):
        return get_ci(self.inputs, INP_ID_LAYOUT_PLANE_SEL, ac.SelectionCommandInput)

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        self.move_comp_cb.b_notify_changed_input(changed_input)

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        con = get_context()

        inl_occ = con.child[CN_INTERNAL]
        locators_occ = inl_occ.child.get_real(CN_KEY_LOCATORS)
        locators_occ.light_bulb = True
        key_placeholders_occ = inl_occ.child[CN_KEY_PLACEHOLDERS]
        key_placeholders_occ.light_bulb = True
        self.move_comp_cb.b_notify_execute_preview(event_args, [locators_occ])

        place_key_placeholders()

        event_args.isValidResult = True


class ExtractKleFileCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()

    @property
    def cmd_name(self) -> str:
        return 'Extract KLE'

    @property
    def tooltip(self) -> str:
        return "Extracts KLE's JSON file from F360 file."

    @property
    def resource_folder(self) -> str:
        return 'Resources/extract_kle'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()

        inl_occ = con.child[CN_INTERNAL]

        if AN_KLE_B64 not in inl_occ.comp_attr:
            raise BadConditionException('KLE file is not loaded.')

        kle_b64 = inl_occ.comp_attr[AN_KLE_B64]
        kle_file_content = zlib.decompress(base64.b64decode(kle_b64))

        dir_dlg = con.ui.createFolderDialog()
        dir_dlg.title = 'Choose Output Folder'
        if dir_dlg.showDialog() != ac.DialogResults.DialogOK:
            return
        output_dir_path = pathlib.Path(dir_dlg.folder)

        with open(output_dir_path / 'extracted_kle.json', 'w+b') as f:
            f.write(kle_file_content)

        con.ui.messageBox('KLE file has been extracted as extracted-kle.json.', 'P2PPCB')
