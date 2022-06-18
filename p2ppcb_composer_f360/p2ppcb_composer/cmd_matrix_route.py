from collections import defaultdict
import typing as ty
import pathlib
import numpy as np
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput, SelectionEventArgs, SelectionCommandInput, Selection
from f360_common import AN_COL_NAME, AN_ROW_NAME, ANS_RC_NAME, CN_MISC_PLACEHOLDERS, BadCodeException, BadConditionException, F3Occurrence, get_context, CN_INTERNAL, CN_KEY_LOCATORS, ORIGIN_P3D
from p2ppcb_composer.cmd_common import AN_MAIN_LAYOUT_PLANE, CommandHandlerBase, get_ci, has_sel_in
from route import route as rt
from p2ppcb_composer.cmd_key_common import INP_ID_KEY_LOCATOR_SEL, get_layout_plane_transform

INP_ID_LEDKEY_BOOL = 'ledKey'
INP_ID_ROW_COL_RADIO = 'rowCol'
INP_ID_WIRE_NAME_DD = 'wireName'


def is_led_name(name):
    return name.startswith('LED')


class AssignMatrixCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.text_color_rc = {
            rt.RC.Row: af.CustomGraphicsSolidColorEffect.create(ac.Color.create(255, 0, 0, 255)),
            rt.RC.Col: af.CustomGraphicsSolidColorEffect.create(ac.Color.create(0, 0, 255, 255)),
        }
        m = ac.Matrix3D.create()
        m.setCell(0, 3, -0.7)
        m.setCell(2, 3, 0.3)
        mr = m.copy()
        mr.setCell(1, 3, -0.6)
        mc = m
        mc.setCell(1, 3, 0.4)
        self.m_rc = {rt.RC.Row: mr, rt.RC.Col: mc}
        self.bb = af.CustomGraphicsBillBoard.create(ORIGIN_P3D)
        self.bb.billBoardStyle = af.CustomGraphicsBillBoardStyles.ScreenBillBoardStyle
        self.last_light_bulb = False

    @property
    def cmd_name(self) -> str:
        return 'Assign Matrix'

    @property
    def tooltip(self) -> str:
        return 'Assigns a matrix for key layout. You can select key locators of a source/drain once and assign a source/drain line.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/assign_matrix'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        inputs = self.inputs
        locator_in = inputs.addSelectionInput(INP_ID_KEY_LOCATOR_SEL, 'Key Locator', 'Select an entity')
        locator_in.addSelectionFilter('Occurrences')
        locator_in.setSelectionLimits(0, 0)

        _ = self.inputs.addBoolValueInput(INP_ID_LEDKEY_BOOL, 'LED key', True)

        rowcol_in = inputs.addRadioButtonGroupCommandInput(INP_ID_ROW_COL_RADIO, 'Source / Drain')
        rowcol_in.listItems.add('Source', True)
        rowcol_in.listItems.add('Drain', False)

        _ = inputs.addDropDownCommandInput(INP_ID_WIRE_NAME_DD, 'Wire Name', ac.DropDownStyles.TextListDropDownStyle)
        self.set_wire_in()

        self.show_billboard()

    def notify_pre_select(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        if active_input.id != INP_ID_KEY_LOCATOR_SEL:
            return
        e = af.Occurrence.cast(selection.entity)
        if e is None:
            event_args.isSelectable = False
            return
        ent = F3Occurrence(e)
        if (not ent.has_parent) or ent.parent.name != CN_KEY_LOCATORS:
            event_args.isSelectable = False
            return
        selected_locators = self.get_selected_locators()
        if len(selected_locators) <= 1:
            return
        is_led = self.get_ledkey_in().value
        for rc in rt.RC:
            if ANS_RC_NAME[rc] in ent.comp_attr and is_led_name(ent.comp_attr[ANS_RC_NAME[rc]]) != is_led:
                event_args.isSelectable = False
                return

    def get_locator_in(self):
        return get_ci(self.inputs, INP_ID_KEY_LOCATOR_SEL, ac.SelectionCommandInput)

    def get_ledkey_in(self):
        return get_ci(self.inputs, INP_ID_LEDKEY_BOOL, ac.BoolValueCommandInput)

    def get_selected_locators(self):
        locator_in = self.get_locator_in()
        return [F3Occurrence(locator_in.selection(i).entity) for i in range(locator_in.selectionCount)]

    def get_rowcol_in(self):
        return get_ci(self.inputs, INP_ID_ROW_COL_RADIO, ac.RadioButtonGroupCommandInput)

    def get_rc(self) -> rt.RC:
        return rt.RC.Row if self.get_rowcol_in().selectedItem.name == 'Source' else rt.RC.Col

    def get_wire_in(self):
        return get_ci(self.inputs, INP_ID_WIRE_NAME_DD, ac.DropDownCommandInput)

    def set_wire_in(self, selected_locators_changed=False):
        wire_in = self.get_wire_in()
        wire_in.listItems.clear()
        rowcol_in = self.get_rowcol_in()
        rc = self.get_rc()
        ledkey_in = self.get_ledkey_in()

        selected_locators = self.get_selected_locators()
        if len(selected_locators) == 0:
            wire_in.isVisible = False
            ledkey_in.isVisible = False
            rowcol_in.isVisible = False
            return
        wire_in.isVisible = True
        ledkey_in.isVisible = True
        rowcol_in.isVisible = True
        wire_in.listItems.add('', True)
        is_first_selected_locators = selected_locators_changed and len(selected_locators) == 1
        selected_wn = ''
        for kl_occ in selected_locators:
            if ANS_RC_NAME[rc] in kl_occ.comp_attr:
                wn = kl_occ.comp_attr[ANS_RC_NAME[rc]]
                if selected_wn == '':
                    selected_wn = wn
                elif selected_wn != wn:
                    selected_wn = ''
                    break
            else:
                selected_wn = ''
                break
        is_led = is_led_name(selected_wn) if is_first_selected_locators else ledkey_in.value

        for wn in rt.get_mainboard_constants().wire_names_rc[rc]:
            if is_led_name(wn) == is_led:
                wire_in.listItems.add(wn, wn == selected_wn)
        if is_first_selected_locators:
            self.get_ledkey_in().value = is_led

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        if changed_input.id == INP_ID_ROW_COL_RADIO:
            self.set_wire_in()
        elif changed_input.id == INP_ID_KEY_LOCATOR_SEL:
            self.set_wire_in(True)
        elif changed_input.id == INP_ID_LEDKEY_BOOL:
            self.set_wire_in()

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs) -> None:
        locator_in = self.get_locator_in()
        wire_in = self.get_wire_in()
        rc = self.get_rc()
        selected_locators = self.get_selected_locators()

        if not has_sel_in(locator_in):
            event_args.areInputsValid = False
            return
        if wire_in.selectedItem.name == '':
            event_args.areInputsValid = False
            return

        matrix_hits: ty.Dict[str, ty.Dict[str, str]] = defaultdict(lambda: defaultdict(str))
        for kl_occ in get_context().child[CN_INTERNAL].child[CN_KEY_LOCATORS].child.values():
            if AN_ROW_NAME in kl_occ.comp_attr and AN_COL_NAME in kl_occ.comp_attr:
                matrix_hits[kl_occ.comp_attr[AN_ROW_NAME]][kl_occ.comp_attr[AN_COL_NAME]] = kl_occ.name
        not_rc = 1 if rc == 0 else 0
        wn = wire_in.selectedItem.name
        for kl_occ in selected_locators:
            if ANS_RC_NAME[not_rc] in kl_occ.comp_attr:
                r = wn
                c = kl_occ.comp_attr[ANS_RC_NAME[not_rc]]
                if rc == 1:
                    r, c = c, r
                if matrix_hits[r][c] != '' and matrix_hits[r][c] != kl_occ.name:
                    event_args.areInputsValid = False
                    return
                else:
                    matrix_hits[r][c] = kl_occ.name

    def add_cg_text(self, kl_occ: F3Occurrence, cg: af.CustomGraphicsGroup, rc: rt.RC):
        cgt = cg.addText(kl_occ.comp_attr[ANS_RC_NAME[rc]], 'Arial', 0.3, self.m_rc[rc])
        cgt.billBoarding = self.bb
        cgt.color = self.text_color_rc[rc]

    def show_billboard(self):
        key_locators = get_context().child[CN_INTERNAL].child[CN_KEY_LOCATORS]
        self.last_light_bulb = key_locators.light_bulb
        key_locators.light_bulb = True
        for kl_occ in key_locators.child.values():
            if not isinstance(kl_occ, F3Occurrence):
                raise BadCodeException()
            cgs = kl_occ.comp.customGraphicsGroups
            for irc in rt.RC:
                cg = cgs.add()
                if ANS_RC_NAME[irc] in kl_occ.comp_attr:
                    self.add_cg_text(kl_occ, cg, irc)

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        self.notify_execute_common(event_args)
        rc = self.get_rc()
        for kl_occ in self.get_selected_locators():
            cg = kl_occ.comp.customGraphicsGroups[rc]
            for cge in list(cg):
                cge.deleteMe()
            if ANS_RC_NAME[rc] in kl_occ.comp_attr:
                self.add_cg_text(kl_occ, cg, rc)

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.notify_execute_common(event_args)

    def notify_execute_common(self, event_args: CommandEventArgs) -> None:
        rc = self.get_rc()
        inv_rc = rt.RC.Col if rc == rt.RC.Row else rt.RC.Row
        is_led = self.get_ledkey_in().value
        for kl_occ in self.get_selected_locators():
            kl_occ.comp_attr[ANS_RC_NAME[rc]] = self.get_wire_in().selectedItem.name
            if ANS_RC_NAME[inv_rc] in kl_occ.comp_attr:
                if is_led_name(kl_occ.comp_attr[ANS_RC_NAME[inv_rc]]) != is_led:
                    del kl_occ.comp_attr[ANS_RC_NAME[inv_rc]]

    def notify_destroy(self, event_args: CommandEventArgs) -> None:
        key_locators = get_context().child[CN_INTERNAL].child[CN_KEY_LOCATORS]
        key_locators.light_bulb = self.last_light_bulb
        for kl_occ in key_locators.child.values():
            if not isinstance(kl_occ, F3Occurrence):
                raise BadCodeException()
            for cg in list(kl_occ.comp.customGraphicsGroups):
                for cge in list(cg):
                    cge.deleteMe()
                cg.deleteMe()


class GenerateRouteCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()

    @property
    def cmd_name(self) -> str:
        return 'Generate Route'

    @property
    def tooltip(self) -> str:
        return 'Generates route data (QMK keymap and wiring diagrams) from a matrix. You should complete the matrix first.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/generate_route'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()
        inl_occ = con.child[CN_INTERNAL]

        matrix: ty.Dict[str, ty.Dict[str, str]] = defaultdict(lambda: defaultdict(str))
        for kl_occ in inl_occ.child[CN_KEY_LOCATORS].child.values():
            if AN_ROW_NAME in kl_occ.comp_attr and AN_COL_NAME in kl_occ.comp_attr:
                matrix[kl_occ.comp_attr[AN_ROW_NAME]][kl_occ.comp_attr[AN_COL_NAME]] = kl_occ.name
            else:
                raise BadConditionException('Assign source/drain to all key locators.')

        mc = rt.get_mainboard_constants()
        if CN_MISC_PLACEHOLDERS not in inl_occ.child or rt.get_cn_mainboard() not in inl_occ.child[CN_MISC_PLACEHOLDERS].child:
            raise BadConditionException('Place a mainboard first.')

        dir_dlg = con.ui.createFolderDialog()
        dir_dlg.title = 'Choose Output Folder'
        if dir_dlg.showDialog() != ac.DialogResults.DialogOK:
            return
        output_dir_path = pathlib.Path(dir_dlg.folder)

        mb_occ = inl_occ.child[CN_MISC_PLACEHOLDERS].child.get_real(rt.get_cn_mainboard())
        lp = af.ConstructionPlane.cast(con.attr_singleton[AN_MAIN_LAYOUT_PLANE][1])
        inv_lp_trans = get_layout_plane_transform(lp)
        inv_lp_trans.invert()
        sk = con.root_comp.sketches.add(lp)
        flat_cable_placements: ty.List[rt.FlatCablePlacement] = []
        for i, cable in enumerate(mc.flat_cables):
            cp_s = mb_occ.comp.constructionPoints.itemByName(f'Cable{i}_Start')
            if cp_s is None:
                raise BadCodeException(f'The mainboard F3D lacks Cable{i}_Start construction point.')
            cp_s = cp_s.createForAssemblyContext(mb_occ.raw_occ)
            cp_e = mb_occ.comp.constructionPoints.itemByName(f'Cable{i}_End')
            if cp_e is None:
                raise BadCodeException(f'The mainboard F3D lacks Cable{i}_End construction point.')
            cp_e = cp_e.createForAssemblyContext(mb_occ.raw_occ)
            oc: ac.ObjectCollectionT[af.SketchPoint] = sk.project(cp_s)  # type: ignore
            start = sk.sketchToModelSpace(oc[0].geometry)
            start.transformBy(inv_lp_trans)
            oc: ac.ObjectCollectionT[af.SketchPoint] = sk.project(cp_e)  # type: ignore
            end = sk.sketchToModelSpace(oc[0].geometry)
            end.transformBy(inv_lp_trans)
            angle = np.pi / 2
            if not start.isEqualToByTolerance(end, 0.01):
                uv = ac.Point3D.create(start.x + 1., start.y, start.z)
                mr = con.app.measureManager.measureAngle(uv, start, end)
                angle = mr.value
            flat_cable_placements.append(rt.FlatCablePlacement((start.x, start.y), angle, cable))
        sk.deleteMe()
        keys_rc, entries_rccp, route_rccp = rt.generate_route(matrix, flat_cable_placements)
        img_row, img_col = rt.draw_wire(keys_rc, entries_rccp, route_rccp)
        generated_snippet, via_json = rt.generate_keymap(keys_rc, mc)

        with open(output_dir_path / 'qmk_keymap.txt', 'w') as f:
            f.write(generated_snippet)
        with open(output_dir_path / 'via_keymap.json', 'w') as f:
            f.write(via_json)
        img_row.save(str(output_dir_path / 'wiring_source.png'))
        img_col.save(str(output_dir_path / 'wiring_drain.png'))

        con.ui.messageBox('QMK / VIA keymap and wiring diagrams has been generated.', 'P2PPCB')
