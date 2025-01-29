import base64
from collections import defaultdict
import pickle
import pathlib
import typing as ty
import itertools
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput, CommandInputs, SelectionCommandInput, \
    SelectionEventArgs, ValidateInputsEventArgs, Selection
from f360_common import AN_HOLE, AN_MEV, AN_MF, AN_TERRITORY, \
    BN_APPEARANCE_HOLE, BN_APPEARANCE_MEV, BN_APPEARANCE_MF, CN_DEPOT_APPEARANCE, CN_INTERNAL, CN_KEY_LOCATORS, CN_KEY_PLACEHOLDERS, \
    ORIGIN_P3D, PARTS_DATA_DIR, XU_V3D, YU_V3D, BadCodeException, BadConditionException, BodyFinder, \
    CreateObjectCollectionT, F3Occurrence, FourOrientation, TwoOrientation, VirtualF3Occurrence, \
    get_context, catch_exception, reset_context, CN_FOOT_PLACEHOLDERS, \
    CN_MISC_PLACEHOLDERS, CNP_KEY_LOCATOR
from p2ppcb_parts_resolver import resolver as parts_resolver
from pint import Quantity


AN_LOCATORS_PLANE_TOKEN = 'locatorsPlaneToken'
AN_MAIN_SURFACE = 'mainSurface'
AN_MAINBOARD = 'mainboard'
AN_MAIN_KEY_ANGLE_SURFACE = 'mainKeyAngleSurface'
AN_MAIN_LAYOUT_PLANE = 'mainLayoutPlane'
AN_MAIN_CAP_DESC = 'mainCapDesc'
AN_MAIN_STABILIZER_DESC = 'mainStabilizerDesc'
AN_MAIN_STABILIZER_ORIENTATION = 'mainStabilizerOrientation'
AN_MAIN_SWITCH_DESC = 'mainSwitchDesc'
AN_MAIN_SWITCH_ORIENTATION = 'mainSwitchOrientation'
AN_MAIN_KEY_V_ALIGN = 'mainKeyVAlign'
AN_MAIN_KEY_V_OFFSET = 'mainKeyVOffset'
ANS_MAIN_OPTION = [AN_MAIN_CAP_DESC, AN_MAIN_STABILIZER_DESC, AN_MAIN_STABILIZER_ORIENTATION, AN_MAIN_SWITCH_DESC, AN_MAIN_SWITCH_ORIENTATION, AN_MAIN_KEY_V_ALIGN]
AN_MB_LOCATION_INPUTS = 'mbLocationInputs'


INP_ID_CAP_DESC_DD = 'capDesc'
INP_ID_STABILIZER_DESC_DD = 'stabilizerDesc'
INP_ID_STABILIZER_ORIENTATION_DD = 'stabilizerOrientation'
INP_ID_SWITCH_DESC_DD = 'switchDesc'
INP_ID_SWITCH_ORIENTATION_DD = 'switchOrientation'
INP_ID_KEY_V_ALIGN_TO_DD = 'keyVAlignTo'
INP_ID_KEY_V_OFFSET_STR = 'keyVOffset'
INPS_ID_OPTION = [INP_ID_CAP_DESC_DD, INP_ID_STABILIZER_DESC_DD, INP_ID_STABILIZER_ORIENTATION_DD, INP_ID_SWITCH_DESC_DD, INP_ID_SWITCH_ORIENTATION_DD, INP_ID_KEY_V_ALIGN_TO_DD]
INP_ID_PARTS_DATA_PATH_BOOL = 'partsDataPath'
INP_ID_SHOW_INF_HOLE_BOOL = 'showHole'
INP_ID_SHOW_INF_MEV_BOOL = 'showMEV'
INP_ID_SHOW_INF_MF_BOOL = 'showMF'
INP_ID_CHECK_INTERFERENCE_BOOL = 'checkInterference'
INP_ID_ROTATION_AV = 'rotationAngle'
INP_ID_X_DV = 'distanceX'
INP_ID_Y_DV = 'distanceY'
INPS_ID_SHOW_HIDE = [INP_ID_ROTATION_AV, INP_ID_X_DV, INP_ID_Y_DV]

TOOLTIP_NOT_SELECTED = 'Not Selected'
TOOLTIPS_PARTS_DIR = ('Parts Data Dir', 'Parts data dir contains the parts data of P2PPCB. Usually p2ppcb_software/p2ppcb_parts_data_f360.')
TOOLTIPS_STABILIZER_ORIENTATION = ('Stabilizer Orientation', 'Front is normal. You can choose this to avoid interference. Choc V1 should be always Front.')
TOOLTIPS_SWITCH_ORIENTATION = ('Switch Orientation', 'Front is normal. You can choose this to avoid interference. Choc V1 should be always Front.')
TOOLTIPS_V_ALIGN = ('Key V-Align', "The anchor point of the vertical alignment. The anchor point is on its skeleton surface.\nStemBottom refers key-up state. TravelBottom refers the cap's top of key-down state.")


class _CommandEventHandler(ac.CommandEventHandler):
    def __init__(self, parent: 'CommandHandlerBase', method_name: str):
        super().__init__()
        self.parent = parent
        self.method_name = method_name

    @catch_exception
    def notify(self, args):
        if not self.parent.create_ok:
            return
        event_args = CommandEventArgs.cast(args)
        inputs = event_args.command.commandInputs
        li = self.parent._inputs
        try:
            self.parent._inputs = inputs
            getattr(self.parent, self.method_name)(event_args)
        finally:
            self.parent._inputs = li


class _ExecuteCommandEventHandler(_CommandEventHandler):
    def __init__(self, parent: 'CommandHandlerBase'):
        super().__init__(parent, 'notify_execute')

    def notify(self, args):
        if self.parent.create_ok:
            super().notify(args)


class _InputChangedHandler(ac.InputChangedEventHandler):  # type: ignore
    def __init__(self, parent: 'CommandHandlerBase'):
        super().__init__()
        self.parent = parent

    @catch_exception
    def notify(self, args):
        if not self.parent.create_ok:
            return
        event_args = ac.InputChangedEventArgs.cast(args)
        changed_input = event_args.input
        inputs = changed_input.commandInputs
        li = self.parent._inputs
        try:
            self.parent._inputs = inputs
            self.parent.notify_input_changed(event_args, changed_input)
        finally:
            self.parent._inputs = li


class _SelectionEventHandler(ac.SelectionEventHandler):  # type: ignore
    def __init__(self, parent: 'CommandHandlerBase', method_name: str):
        super().__init__()
        self.parent = parent
        self.method_name = method_name

    @catch_exception
    def notify(self, args):
        if not self.parent.create_ok:
            return
        event_args = SelectionEventArgs.cast(args)
        active_input = event_args.activeInput
        selection = event_args.selection
        li = self.parent._inputs
        try:
            if active_input is None:
                self.parent._inputs = None
            else:
                self.parent._inputs = active_input.commandInputs
            getattr(self.parent, self.method_name)(event_args, active_input, selection)
        finally:
            self.parent._inputs = li


class _ValidateEventHandler(ac.ValidateInputsEventHandler):  # type: ignore
    def __init__(self, parent: 'CommandHandlerBase'):
        super().__init__()
        self.parent = parent

    @catch_exception
    def notify(self, args):
        if not self.parent.create_ok:
            return
        event_args = ac.ValidateInputsEventArgs.cast(args)
        inputs = event_args.inputs
        li = self.parent._inputs
        try:
            self.parent._inputs = inputs
            self.parent.notify_validate(event_args)
        finally:
            self.parent._inputs = li


class CommandHandlerBase(ac.CommandCreatedEventHandler):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self._inputs: ty.Optional[ac.CommandInputs] = None
        self.create_ok: bool
        self.require_cn_internal = True
        self.require_cn_key_locators = True

    @property
    def cmd_name(self) -> str:
        raise NotImplementedError('cmd_name is not implemented.')

    @property
    def tooltip(self) -> str:
        raise NotImplementedError('tooltip is not implemented.')

    @property
    def resource_folder(self) -> str:
        raise NotImplementedError('resource_folder is not implemented.')

    @property
    def inputs(self) -> ac.CommandInputs:
        if self._inputs is None:
            raise BadCodeException('CommandInputs is not available here.')
        return self._inputs

    @catch_exception
    def notify(self, args):
        event_args = ac.CommandCreatedEventArgs.cast(args)
        command = event_args.command

        if hasattr(self, 'notify_input_changed'):
            self.on_input_changed = _InputChangedHandler(self)
            command.inputChanged.add(self.on_input_changed)

        if hasattr(self, 'notify_validate'):
            self.on_validate = _ValidateEventHandler(self)
            command.validateInputs.add(self.on_validate)

        self.command_event = {}
        for mn, pn in [
                ('notify_activate', 'activate'),
                ('notify_deactivate', 'deactivate'),
                ('notify_destroy', 'destroy'),
                ('notify_execute_preview', 'executePreview')]:
            if hasattr(self, mn):
                self.command_event[mn] = _CommandEventHandler(self, mn)
                getattr(command, pn).add(self.command_event[mn])

        if hasattr(self, 'notify_execute'):
            self.command_event['notify_execute'] = _ExecuteCommandEventHandler(self)
            command.execute.add(self.command_event['notify_execute'])

        self.selection_event = {}
        for mn, pn in [
                ('notify_pre_select', 'preSelect'),
                ('notify_pre_select_end', 'preSelectEnd'),
                ('notify_select', 'select'),
                ('notify_unselect', 'unselect')]:
            if hasattr(self, mn):
                self.selection_event[mn] = _SelectionEventHandler(self, mn)
                getattr(command, pn).add(self.selection_event[mn])

        self._inputs = command.commandInputs
        reset_context()
        self.create_ok = True
        try:
            con = get_context()
            if self.require_cn_internal and CN_INTERNAL not in con.child:
                con.ui.messageBox('Please initialize a P2PPCB project first.')
                self.create_ok = False
                return
            if self.require_cn_key_locators and CN_KEY_LOCATORS not in con.child[CN_INTERNAL].child:
                con.ui.messageBox('Please load KLE first.')
                self.create_ok = False
                return
            self.notify_create(event_args)
        except Exception as e:
            self.create_ok = False
            raise e
        finally:
            self._inputs = None

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        '''
        InputChangedEventHandler.notify()
        '''
        pass

    def notify_validate(self, event_args: ValidateInputsEventArgs) -> None:
        '''
        ValidateInputsEventHandler.notify()
        '''
        pass

    def notify_destroy(self, event_args: CommandEventArgs) -> None:
        '''
        destructor of CommandEventHandler.notify()
        '''
        pass

    def notify_deactivate(self, event_args: CommandEventArgs) -> None:
        '''
        deactivate of CommandEventHandler.notify()
        '''
        pass

    def notify_activate(self, event_args: CommandEventArgs) -> None:
        '''
        activate of CommandEventHandler.notify()
        '''
        pass

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        '''
        exec of CommandEventHandler.notify()
        '''
        pass

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        '''
        exec preview of CommandEventHandler.notify()
        '''
        pass

    def notify_pre_select(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        '''
        preSelect of SelectionEventHandler.notify()
        '''
        pass

    def notify_pre_select_end(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        '''
        preSelectEnd of SelectionEventHandler.notify()
        active_input is always None. CommandInputs is not available.
        '''
        pass

    def notify_select(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        '''
        select of SelectionEventHandler.notify()
        active_input is always None. CommandInputs is not available.
        '''
        pass

    def notify_unselect(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        '''
        unselect of SelectionEventHandler.notify()
        active_input is always None. CommandInputs is not available.
        '''
        pass

    def notify_create(self, event_args: CommandCreatedEventArgs) -> None:
        '''
        CommandCreatedEventHandler.notify()
        '''
        pass


def get_ci(inputs: CommandInputs, in_id: str, cls: ty.Type):
    return cls.cast(inputs.itemById(in_id))


def get_cis(inputs: CommandInputs, ins_id: ty.List[str], cls: ty.Type):
    return tuple(cls.cast(inputs.itemById(in_id)) for in_id in ins_id)


def has_sel_in(sel_in: ac.SelectionCommandInput):
    return sel_in.selectionCount > 0 and sel_in.selection(0).entity is not None


def all_has_sel_ins(sel_ins: ty.Iterable[ac.SelectionCommandInput]):
    return all([has_sel_in(sel_in) for sel_in in sel_ins])


class PartsCommandBlock:
    def __init__(self, parent: CommandHandlerBase, parts_data_path: ty.Optional[pathlib.Path] = None):
        self.parts_data_path = parts_data_path
        self.choose_path = parts_data_path is None
        self.parent = parent

    def get_parts_data_in(self):
        return ac.BoolValueCommandInput.cast(self.parent.inputs.itemById(INP_ID_PARTS_DATA_PATH_BOOL))

    def get_option_ins(self) -> ty.Tuple[ac.DropDownCommandInput, ...]:
        return get_cis(self.parent.inputs, INPS_ID_OPTION, ac.DropDownCommandInput)

    def get_selected_options(self):
        return [inp.selectedItem.name for inp in self.get_option_ins()]

    def get_v_offset_in(self):
        return ac.StringValueCommandInput.cast(self.parent.inputs.itemById(INP_ID_KEY_V_OFFSET_STR))

    def get_v_offset(self) -> ty.Optional[float]:
        vo = self.get_v_offset_in().value
        try:
            return Quantity(vo).m_as('cm')  # type: ignore
        except:  # noqa: E722
            return None

    def set_parts_data_path(self, path: pathlib.Path):
        if self.parts_data_path == path and self.choose_path:
            return
        self.pi = parts_resolver.PartsInfo(path / parts_resolver.PARTS_INFO_DIRNAME)
        self.parts_data_path = path
        if self.choose_path:
            pi_in = self.get_parts_data_in()
            pi_in.text = self.parts_data_path.name
        for items, inp in zip([
            self.pi.enumerate_description(parts_resolver.Part.Cap),
            self.pi.enumerate_description(parts_resolver.Part.Stabilizer),
            [d.name for d in TwoOrientation],
            self.pi.enumerate_description(parts_resolver.Part.Switch),
            [d.name for d in FourOrientation],
            [at.name for at in parts_resolver.AlignTo]
        ], self.get_option_ins()):
            li = inp.listItems
            li.clear()
            li.add('', False, '', -1)  # unselected
            for i, item in enumerate(items):
                li.add(item, i == 0, '', -1)

    def notify_create(self, event_args: CommandCreatedEventArgs):
        inputs = self.parent.inputs
        if self.choose_path:
            i = inputs.addBoolValueInput(INP_ID_PARTS_DATA_PATH_BOOL, 'Parts Data Dir', False)
            i.tooltip, i.tooltipDescription = TOOLTIPS_PARTS_DIR
        _ = inputs.addDropDownCommandInput(INP_ID_CAP_DESC_DD, 'Cap', ac.DropDownStyles.TextListDropDownStyle)
        _ = inputs.addDropDownCommandInput(INP_ID_STABILIZER_DESC_DD, 'Stabilizer', ac.DropDownStyles.TextListDropDownStyle)
        i = inputs.addDropDownCommandInput(INP_ID_STABILIZER_ORIENTATION_DD, 'Stabilizer Orientation', ac.DropDownStyles.TextListDropDownStyle)
        i.tooltip, i.tooltipDescription = TOOLTIPS_STABILIZER_ORIENTATION
        _ = inputs.addDropDownCommandInput(INP_ID_SWITCH_DESC_DD, 'Switch', ac.DropDownStyles.TextListDropDownStyle)
        i = inputs.addDropDownCommandInput(INP_ID_SWITCH_ORIENTATION_DD, 'Switch Orientation', ac.DropDownStyles.TextListDropDownStyle)
        i.tooltip, i.tooltipDescription = TOOLTIPS_SWITCH_ORIENTATION
        i = inputs.addDropDownCommandInput(INP_ID_KEY_V_ALIGN_TO_DD, 'Key V-Align', ac.DropDownStyles.TextListDropDownStyle)
        i.tooltip, i.tooltipDescription = TOOLTIPS_V_ALIGN
        _ = inputs.addStringValueInput(INP_ID_KEY_V_OFFSET_STR, 'Key V-Offset', '0 mm')
        self.set_parts_data_path(PARTS_DATA_DIR if self.parts_data_path is None else self.parts_data_path)

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs):
        vo_in = self.get_v_offset_in()
        try:
            if not Quantity(vo_in.value).check('mm'):  # type: ignore
                vo_in.isValueError = True
                event_args.areInputsValid = False
        except:  # noqa: E722
            vo_in.isValueError = True
            event_args.areInputsValid = False

    def b_notify_input_changed(self, changed_input: CommandInput):
        if changed_input.id == INP_ID_PARTS_DATA_PATH_BOOL:
            con = get_context()
            fd = con.ui.createFolderDialog()
            fd.initialDirectory = str(self.parts_data_path)
            fd.title = 'Choose parts data Dir'
            if fd.showDialog() != ac.DialogResults.DialogOK:
                return
            path = pathlib.Path(fd.folder)
            try:
                self.set_parts_data_path(path)
            except Exception:
                con.ui.messageBox('The directory is not parts data dir.')

    def deselect(self):
        for inp in self.get_option_ins():
            for li in inp.listItems:
                li.isSelected = False
        vo_in = self.get_v_offset_in()
        vo_in.value = ''

    def show_hide(self, is_visible: bool):
        for inp in self.get_option_ins():
            inp.isVisible = is_visible
        self.get_v_offset_in().isVisible = is_visible
        if self.choose_path:
            self.get_parts_data_in().isVisible = is_visible


class InputLocators:
    def __init__(self, inp: SelectionCommandInput, attr_name: str) -> None:
        self.inp = inp
        self.attr_name = attr_name
    
    def get_locators_attr_value(self, selected_locators: ty.List[F3Occurrence]) -> ty.Optional[str]:
        v: ty.Optional[str] = ''
        for ent in selected_locators:
            if self.attr_name not in ent.comp_attr:
                raise BadConditionException('This file is corrupted.')
            n = ent.comp_attr[self.attr_name]
            if v == '':
                v = n
            elif v == n:
                continue
            else:
                v = None
                break
        return v

    def set_locators_attr_value(self, selected_locators: ty.List[F3Occurrence], v: str):
        for ent in selected_locators:
            ent.comp_attr[self.attr_name] = v

    def hide(self):
        self.inp.clearSelection()
        self.inp.isVisible = False

    def show(self, selected_locators: ty.List[F3Occurrence]):
        self.show_by_token(self.get_locators_attr_value(selected_locators))
    
    def show_by_token(self, token: ty.Optional[str]):
        self.inp.isVisible = True
        if token is None:
            self.inp.clearSelection()
            self.inp.tooltip = TOOLTIP_NOT_SELECTED
        else:
            es = get_context().find_by_token(token)
            if len(es) == 0:
                self.inp.clearSelection()
                self.inp.tooltip = TOOLTIP_NOT_SELECTED
            else:
                ent = es[0]
                if not has_sel_in(self.inp):
                    self.inp.addSelection(ent)
                else:
                    current_ent = self.inp.selection(0).entity
                    if current_ent != ent:
                        self.inp.clearSelection()
                        self.inp.addSelection(ent)
                self.inp.tooltip = ent.name  # type: ignore


def get_selected_locators(locator_in: ac.SelectionCommandInput):
    return list([
        F3Occurrence(ty.cast(af.BRepBody, locator_in.selection(i).entity).assemblyContext)
        for i in range(locator_in.selectionCount)
    ])


def locator_notify_pre_select(inp_id: str, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection):
    e: af.BRepBody = selection.entity  # type: ignore
    if not e.parentComponent.name.endswith(CNP_KEY_LOCATOR) or e.assemblyContext is None or e.assemblyContext.assemblyContext is None or e.assemblyContext.assemblyContext.component.name != CN_KEY_LOCATORS:
        event_args.isSelectable = False
        return
    con = get_context()
    lp_ci = InputLocators(active_input, AN_LOCATORS_PLANE_TOKEN)
    preselect_lp_token = lp_ci.get_locators_attr_value([F3Occurrence(e.assemblyContext)])
    if preselect_lp_token is None:
        raise BadCodeException('Internal Error: Key locator lacks lp_token.')
    preselect_lp = con.find_by_token(preselect_lp_token)[0]
    locator_in = get_ci(active_input.commandInputs, inp_id, ac.SelectionCommandInput)
    if has_sel_in(locator_in):
        selected_lp_token = lp_ci.get_locators_attr_value(get_selected_locators(locator_in))
        if selected_lp_token is not None and len(selected_lp_token) > 0:
            selected_lp = con.find_by_token(selected_lp_token)[0]
            if preselect_lp != selected_lp:
                event_args.isSelectable = False


def _check_interference(category_enables: ty.Dict[str, bool], move_occs: ty.List[F3Occurrence], right_flip: ty.Optional[str]) -> ty.Tuple[ty.List[af.BRepBody], ty.List[af.BRepBody], ty.List[af.BRepBody], ty.Set[F3Occurrence], ty.List[ty.Tuple[af.BRepBody, af.BRepBody]]]:  # noqa
    con = get_context()
    inl_occ = con.child[CN_INTERNAL]

    other_occs = []
    for cn in [CN_KEY_PLACEHOLDERS, CN_FOOT_PLACEHOLDERS, CN_MISC_PLACEHOLDERS]:
        if cn in inl_occ.child:
            for o in inl_occ.child[cn].child.values():
                if o.light_bulb and isinstance(o, F3Occurrence):
                    other_occs.append(o)

    cache_temp_body: ty.List[ty.Tuple[af.BRepBody, af.BRepBody]] = []
    body_finder = BodyFinder()
    col = CreateObjectCollectionT(af.BRepBody)  # optimization to avoid ObjectCollection.create().

    def _get_temp_body(orig_body: af.BRepBody):
        for ob, tb in cache_temp_body:
            if ob == orig_body:
                return tb
        tb = orig_body.copyToComponent(con.comp)  # copyToComponent() is deadly slow.
        tb.isLightBulbOn = False
        cache_temp_body.append((orig_body, tb))
        return tb

    def _analyze_interference(msg: str, left_part_occ: VirtualF3Occurrence, right_part_occ: VirtualF3Occurrence) -> list[tuple[af.BRepBody, af.BRepBody]]:
        if len(col) < 2:
            return []

        inf_results = con.des.analyzeInterference(con.des.createInterferenceInput(col))
        if inf_results is None:
            con.ui.messageBox(f'You have encountered a bug of Fusion 360. The interference check is invalid about {msg} of\n{left_part_occ.name} in {left_part_occ.parent.raw_occ.fullPathName}\nand\n{right_part_occ.name} in {right_part_occ.parent.raw_occ.fullPathName}.\nAbout the bug:\nhttps://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251')  # noqa: E501
            return []
        if len(inf_results) == 0:
            return []

        nbs: list = [b.nativeObject for b in col]
        ret: list[tuple[af.BRepBody, af.BRepBody]] = []
        for ir in inf_results:
            p0 = ir.interferenceBody.vertices[0].geometry
            lr: list[af.BRepBody] = []

            # entityOne and entityTwo lacks assemblyContext. So we need to find it.
            for e in [ir.entityOne, ir.entityTwo]:
                cs1: list[af.BRepBody] = []
                try:
                    s = 0
                    while True:
                        hit = nbs.index(e, s)
                        s = hit + 1
                        cs1.append(col[hit])
                except ValueError:
                    pass
                if len(cs1) == 0:
                    raise BadCodeException()
                elif len(cs1) == 1:
                    lr.append(cs1[0])
                else:
                    cs2: list[af.BRepBody] = []
                    for c in cs1:
                        if c.pointContainment(p0) == af.PointContainment.PointOnPointContainment:
                            cs2.append(c)
                    if len(cs2) == 0:
                        raise BadCodeException()
                    elif len(cs2) == 1:
                        lr.append(cs2[0])
                    else:
                        hits: list[bool] = [True] * len(cs2)
                        for p in [v.geometry for v in ir.interferenceBody.vertices]:
                            for i, c in enumerate(cs2):
                                if hits[i] and c.pointContainment(p) != af.PointContainment.PointOnPointContainment:
                                    hits[i] = False
                                if sum(hits) == 1:
                                    break
                            if sum(hits) == 1:
                                break
                        if sum(hits) == 2:
                            # no way to distinguish cs[0] and cs[1].
                            lr = cs2
                            break
                        if sum(hits) != 1:
                            raise BadCodeException()
                        lr.append(cs2[hits.index(True)])
            handedness: list[ty.Optional[bool]] = [None, None]
            for i, b in enumerate(lr):
                raw_occ = b.assemblyContext
                while True:
                    if raw_occ is None:
                        break
                    elif raw_occ == left_part_occ.raw_occ:
                        handedness[i] = True
                    elif raw_occ == right_part_occ.raw_occ:
                        handedness[i] = False
                    else:
                        raw_occ = raw_occ.assemblyContext
                        continue
                    break
            if handedness[0] == handedness[1]:  # intra inf
                continue
            if handedness[0] is None or handedness[1] is None:
                raise BadCodeException()
            if handedness[1]:
                lr = lr[::-1]
            ret.append((lr[0], lr[1]))
        return ret

    def _check_mev_mev(left_part_occ: VirtualF3Occurrence, right_part_occ: VirtualF3Occurrence) -> list[tuple[af.BRepBody, af.BRepBody]]:
        col.clear()
        for o in [left_part_occ, right_part_occ]:
            for b in body_finder.get(o, AN_MEV, AN_MEV) + ([] if right_flip is None else body_finder.get(o, AN_MEV, right_flip)):
                col.add(b)
        return _analyze_interference('MEV - MEV', left_part_occ, right_part_occ)

    def _check_mf_hole(left_part_occ: VirtualF3Occurrence, right_part_occ: VirtualF3Occurrence):
        ret: list[tuple[af.BRepBody, af.BRepBody]] = []
        for hole in body_finder.get(right_part_occ, AN_HOLE, AN_HOLE) + ([] if right_flip is None else body_finder.get(right_part_occ, AN_HOLE, right_flip)):
            col.clear()
            col.add(hole)
            for mf in body_finder.get(left_part_occ, AN_MF, AN_MF) + ([] if right_flip is None else body_finder.get(left_part_occ, AN_MF, right_flip)):
                col.add(mf)
            ret.extend(_analyze_interference('MF - Hole', left_part_occ, right_part_occ))
        return ret

    intersect_pairs: set[tuple[F3Occurrence, F3Occurrence]] = set()
    checked_pairs: set[frozenset[F3Occurrence]] = set()
    territory_bb_cache: dict[F3Occurrence, ac.BoundingBox3D] = {}
    for oo, mo in itertools.product(other_occs, move_occs):
        if oo == mo:
            continue
        p = frozenset({mo, oo})
        if p in checked_pairs:
            continue
        checked_pairs.add(p)

        bbs = []
        for o in [oo, mo]:
            if o in territory_bb_cache:
                bb = territory_bb_cache[o]
            else:
                tbs = body_finder.get(o, AN_TERRITORY)
                if len(tbs) == 0:
                    raise BadCodeException(f'Part {o.name} lacks Territory body.')
                bb = tbs[0].boundingBox.copy()
                for tb in tbs[1:]:
                    bb.combine(tb.boundingBox)
                territory_bb_cache[o] = bb
            bbs.append(bb)
        if bbs[0].intersects(bbs[1]):
            intersect_pairs.add((mo, oo))

    hit_mevs: ty.List[af.BRepBody] = []
    hit_holes: ty.List[af.BRepBody] = []
    hit_mfs: ty.List[af.BRepBody] = []
    hit_occs: ty.Set[F3Occurrence] = set()

    for move_occ, other_occ in intersect_pairs:
        hit = False
        if category_enables[AN_MEV]:
            for mevs in _check_mev_mev(other_occ, move_occ):
                hit = True
                hit_mevs.extend([_get_temp_body(b) for b in mevs])
        if category_enables[AN_MF] or category_enables[AN_HOLE]:
            for mf, hole in _check_mf_hole(other_occ, move_occ) + _check_mf_hole(move_occ, other_occ):
                hit = True
                if category_enables[AN_MF]:
                    hit_mfs.append(_get_temp_body(mf))
                if category_enables[AN_HOLE]:
                    hit_holes.append(_get_temp_body(hole))
        if hit:
            hit_occs.add(move_occ)
            hit_occs.add(other_occ)

    return hit_mevs, hit_holes, hit_mfs, hit_occs, cache_temp_body


class CheckInterferenceCommandBlock:
    def __init__(self, parent: CommandHandlerBase) -> None:
        super().__init__()
        self.hits_on_body_category: ty.Dict[str, ty.Set[ty.Tuple[str, str, str]]] = defaultdict(set)
        self.parent = parent

    def get_checkbox_ins(self) -> ty.Tuple[ac.BoolValueCommandInput, ...]:
        return get_cis(self.parent.inputs, [INP_ID_CHECK_INTERFERENCE_BOOL, INP_ID_SHOW_INF_HOLE_BOOL, INP_ID_SHOW_INF_MF_BOOL, INP_ID_SHOW_INF_MEV_BOOL], ac.BoolValueCommandInput)

    def notify_create(self, event_args: CommandCreatedEventArgs) -> None:
        if_in = self.parent.inputs.addBoolValueInput(INP_ID_CHECK_INTERFERENCE_BOOL, 'Check Interference', True)
        if_in.isVisible = False
        if_in.value = False
        hole_in = self.parent.inputs.addBoolValueInput(INP_ID_SHOW_INF_HOLE_BOOL, 'Hole', True)
        hole_in.isVisible = False
        hole_in.value = False
        mf_in = self.parent.inputs.addBoolValueInput(INP_ID_SHOW_INF_MF_BOOL, 'Must Fill', True)
        mf_in.isVisible = False
        mf_in.value = False
        mev_in = self.parent.inputs.addBoolValueInput(INP_ID_SHOW_INF_MEV_BOOL, 'Must Excl. Void', True)
        mev_in.isVisible = False
        mev_in.value = False

    def show(self, show: bool):
        for cb in self.get_checkbox_ins()[1:]:
            cb.isVisible = show
            cb.value = show

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        if changed_input.id == INP_ID_CHECK_INTERFERENCE_BOOL:
            self.show(self.get_checkbox_ins()[0].value)

    def b_notify_execute_preview(self, move_occs: ty.List[F3Occurrence], av: ty.Optional[str] = None) -> ty.Optional[ty.Tuple[ty.List[af.BRepBody], ty.List[af.BRepBody], ty.List[af.BRepBody], ty.Set[F3Occurrence], ty.List[ty.Tuple[af.BRepBody, af.BRepBody]]]]:
        if len(move_occs) == 0:
            return None
        checkbox_ins = self.get_checkbox_ins()
        if (not checkbox_ins[0].value) or (not any(ci.value for ci in checkbox_ins[1:])):
            return None
        result = self.check_interference(move_occs, av)
        hit_mevs, hit_holes, hit_mfs, hit_occs, _ = result

        for o in hit_occs:
            o.light_bulb = False

        category_appearance = get_category_appearance()
        for hit_bodies, category in zip([hit_mevs, hit_holes, hit_mfs], [AN_MEV, AN_HOLE, AN_MF]):
            for b in hit_bodies:
                b.isLightBulbOn = True
                b.appearance = category_appearance[category]

        return result

    def check_interference(self, move_occs: ty.List[F3Occurrence], av: ty.Optional[str]) -> ty.Tuple[ty.List[af.BRepBody], ty.List[af.BRepBody], ty.List[af.BRepBody], ty.Set[F3Occurrence], ty.List[ty.Tuple[af.BRepBody, af.BRepBody]]]:
        category_enables: ty.Dict[str, bool] = {
            cn: inp.value
            for cn, inp in zip([AN_HOLE, AN_MF, AN_MEV], self.get_checkbox_ins()[1:])
        }
        pb = get_context().ui.progressBar
        try:
            pb.show('Checking Interference...', 0, 1, True)
            return _check_interference(category_enables, move_occs, av)
        finally:
            pb.hide()


class MoveComponentCommandBlock:
    def __init__(self, parent: CommandHandlerBase) -> None:
        self.transaction_trans: ty.Optional[ac.Matrix3D] = None
        self.parent = parent

    def show_hide_ins(self, inps_id: ty.List[str], is_show: bool):
        for inp_id in inps_id:
            inp = self.parent.inputs.itemById(inp_id)
            if inp is None:
                raise BadCodeException(f"{inp_id} didn't find in inputs.")
            inp.isEnabled = is_show
            inp.isVisible = is_show
            if not is_show:
                inp.value = 0.  # type: ignore

    def get_inputs(self):
        inputs = self.parent.inputs
        angle_in = ac.AngleValueCommandInput.cast(inputs.itemById(INP_ID_ROTATION_AV))
        x_in = ac.DistanceValueCommandInput.cast(inputs.itemById(INP_ID_X_DV))
        y_in = ac.DistanceValueCommandInput.cast(inputs.itemById(INP_ID_Y_DV))
        return x_in, y_in, angle_in

    def start_transaction(self, transaction_trans: ac.Matrix3D):
        self.transaction_trans = transaction_trans
        self.show_hide_ins(INPS_ID_SHOW_HIDE, True)
        self.b_notify_changed_input(None)

    def stop_transaction(self):
        self.transaction_trans = None
        self.show_hide_ins(INPS_ID_SHOW_HIDE, False)

    def in_transaction(self):
        return self.transaction_trans is not None

    def b_notify_changed_input(self, changed_input: ty.Optional[CommandInput]):
        if self.transaction_trans is None:
            return

        origin = ac.Point3D.create(0, 0, 0)
        origin.transformBy(self.transaction_trans)
        vx = ac.Vector3D.create(1, 0, 0)
        vx.transformBy(self.transaction_trans)
        vy = ac.Vector3D.create(0, 1, 0)
        vy.transformBy(self.transaction_trans)

        x_in, y_in, angle_in = self.get_inputs()
        cid = '' if changed_input is None else changed_input.id
        if cid != INP_ID_ROTATION_AV:
            o = origin.copy()
            o.transformBy(self.get_mov_trans(x_in.value, y_in.value))
            angle_in.setManipulator(o, vx, vy)
        if cid != INP_ID_X_DV:
            o = origin.copy()
            o.transformBy(self.get_mov_trans(0., y_in.value))
            x_in.setManipulator(o, vx)
        if cid != INP_ID_Y_DV:
            o = origin.copy()
            o.transformBy(self.get_mov_trans(x_in.value, 0.))
            y_in.setManipulator(o, vy)

    def notify_create(self, event_args: CommandCreatedEventArgs):
        inputs = self.parent.inputs
        angle_in = inputs.addAngleValueCommandInput(INP_ID_ROTATION_AV, 'Rotation Angle', ac.ValueInput.createByString('0 degree'))
        angle_in.hasMinimumValue = False
        angle_in.hasMaximumValue = False

        x_in = inputs.addDistanceValueCommandInput(INP_ID_X_DV, 'X', ac.ValueInput.createByString('0 mm'))
        x_in.hasMinimumValue = False
        x_in.hasMaximumValue = False

        y_in = inputs.addDistanceValueCommandInput(INP_ID_Y_DV, 'Y', ac.ValueInput.createByString('0 mm'))
        y_in.hasMinimumValue = False
        y_in.hasMaximumValue = False

        self.show_hide_ins(INPS_ID_SHOW_HIDE, False)

    def get_mov_trans(self, dist_x: float, dist_y: float):
        v = ac.Vector3D.create(dist_x, dist_y, 0.)
        t = self.transaction_trans
        if t is None:
            raise BadCodeException()
        v.transformBy(t)
        mov = ac.Matrix3D.create()
        mov.setCell(0, 3, v.x)
        mov.setCell(1, 3, v.y)
        mov.setCell(2, 3, v.z)
        return mov

    def get_rot_mov_trans(self):
        x_input, y_input, angle_input = self.get_inputs()
        if self.transaction_trans is not None:
            origin = ac.Point3D.create(0, 0, 0)
            origin.transformBy(self.transaction_trans)
            z = ac.Vector3D.create(0, 0, 1)
            z.transformBy(self.transaction_trans)
            rot = ac.Matrix3D.create()
            rot.setToRotation(angle_input.value, z, origin)
            return rot, self.get_mov_trans(x_input.value, y_input.value)
        return None, None

    def b_notify_execute_preview(self, event_args: CommandEventArgs, selections: ty.List[F3Occurrence]) -> None:
        if self.transaction_trans is not None:
            rot, mov = self.get_rot_mov_trans()
            if rot is None or mov is None:
                raise BadCodeException()
            for occ in selections:
                sel_trans = occ.transform
                t = sel_trans.copy()
                t.transformBy(rot)
                t.transformBy(mov)
                occ.transform = t


CUSTOM_EVENT_HANDLERS: ty.Dict[str, ac.CustomEventHandler] = {}
CUSTOM_EVENT_EVENTS: ty.Dict[str, ac.CustomEvent] = {}


class OnceEventHandler(ac.CustomEventHandler):
    def __init__(self, event_id: str) -> None:
        super().__init__()
        self.event_id = event_id
        con = get_context()
        con.app.unregisterCustomEvent(event_id)
        event = con.app.registerCustomEvent(event_id)
        event.add(self)
        CUSTOM_EVENT_HANDLERS[event_id] = self
        CUSTOM_EVENT_EVENTS[event_id] = event
        con.app.fireCustomEvent(event_id)

    @catch_exception
    def notify(self, _) -> None:
        event = CUSTOM_EVENT_EVENTS[self.event_id]
        event.remove(CUSTOM_EVENT_HANDLERS[self.event_id])
        get_context().app.unregisterCustomEvent(self.event_id)
        del CUSTOM_EVENT_EVENTS[self.event_id]
        del CUSTOM_EVENT_HANDLERS[self.event_id]
        self.notify_event()

    def notify_event(self):
        raise NotImplementedError('notify_event() not implemented.')


def check_layout_plane(cp: af.ConstructionPlane) -> ac.Plane:
    t = cp.transform
    cp_o = ORIGIN_P3D.copy()
    cp_o.transformBy(t)
    cp_vx = XU_V3D.copy()
    cp_vx.transformBy(t)
    cp_vy = YU_V3D.copy()
    cp_vy.transformBy(t)
    cp_plane = ac.Plane.createUsingDirections(cp_o, cp_vx, cp_vy)
    z_axis_line = ac.Line3D.create(ORIGIN_P3D, ac.Point3D.create(0, 0, 1))
    if cp_plane.isParallelToLine(z_axis_line):
        raise BadConditionException('Layout Plane cannot be parallel to Z axis.')
    if cp_plane.normal.z < 0.:
        cp_vy.scaleBy(-1.)
        cp_plane = ac.Plane.createUsingDirections(cp_o, cp_vx, cp_vy)
    return cp_plane


def get_category_appearance():
    depot_appearance_occ = get_context().child[CN_INTERNAL].child[CN_DEPOT_APPEARANCE]
    category_appearance: ty.Dict[str, ac.Appearance] = {}
    for category, bn in zip([AN_HOLE, AN_MF, AN_MEV], [BN_APPEARANCE_HOLE, BN_APPEARANCE_MF, BN_APPEARANCE_MEV]):
        cat_b = depot_appearance_occ.raw_occ.bRepBodies.itemByName(bn)
        if cat_b is None:
            raise BadCodeException(f'appearance.f3d is corrupted. It lacks {bn} body.')
        category_appearance[category] = cat_b.appearance
    return category_appearance


def load_mb_location_inputs(o: VirtualF3Occurrence) -> ty.Tuple[ty.Tuple[float, float, float], float, str, bool]:
    return pickle.loads(base64.b64decode(o.comp_attr[AN_MB_LOCATION_INPUTS]))
