from collections import defaultdict
import pathlib
import typing as ty
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput, CommandInputs, SelectionCommandInput,\
    SelectionEventArgs, ValidateInputsEventArgs, Selection
from f360_common import AN_HOLE, AN_LOCATORS_I, AN_LOCATORS_PATTERN_NAME, AN_LOCATORS_SPECIFIER, AN_MEV, AN_MF, AN_TERRITORY, ANS_OPTION, \
    ATTR_GROUP, BN_APPEARANCE_HOLE, BN_APPEARANCE_MEV, BN_APPEARANCE_MF, CN_DEPOT_APPEARANCE, CN_INTERNAL, CN_KEY_LOCATORS, CN_KEY_PLACEHOLDERS, \
    CNP_KEY_ASSEMBLY, CNP_PARTS, MAGIC, ORIGIN_P3D, PARTS_DATA_DIR, XU_V3D, YU_V3D, \
    CreateObjectCollectionT, F3Occurrence, FourOrientation, TwoOrientation, VirtualF3Occurrence, \
    get_context, key_assembly_name, key_placeholder_name, catch_exception, reset_context
from p2ppcb_parts_resolver import resolver as parts_resolver
from pint import Quantity


AN_LOCATORS_PLANE_TOKEN = 'locatorsPlaneToken'
AN_SKELETON_SURFACE = 'skeletonSurface'
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


class _CommandEventHandler(ac.CommandEventHandler):  # type: ignore
    def __init__(self, parent: 'CommandHandlerBase', method_name: str):
        super().__init__()
        self.parent = parent
        self.method_name = method_name

    @catch_exception
    def notify(self, args):
        event_args = CommandEventArgs.cast(args)
        inputs = event_args.command.commandInputs
        li = self.parent._inputs
        try:
            self.parent._inputs = inputs
            getattr(self.parent, self.method_name)(event_args)
        except Exception as e:
            get_context().ui.messageBox(f'Unhandled exception:\n{str(e)}')
        finally:
            self.parent._inputs = li


class _ExecuteCommandEventHandler(_CommandEventHandler):
    def __init__(self, parent: _CommandEventHandler):
        super().__init__(parent, 'notify_execute')

    def notify(self, args):
        if self.parent.run_execute:
            super().notify(args)


class _InputChangedHandler(ac.InputChangedEventHandler):  # type: ignore
    def __init__(self, parent: 'CommandHandlerBase'):
        super().__init__()
        self.parent = parent

    @catch_exception
    def notify(self, args):
        event_args = ac.InputChangedEventArgs.cast(args)
        changed_input = event_args.input
        inputs = changed_input.commandInputs
        li = self.parent._inputs
        try:
            self.parent._inputs = inputs
            self.parent.notify_input_changed(event_args, changed_input)
        except Exception as e:
            get_context().ui.messageBox(f'Unhandled exception:\n{str(e)}')
        finally:
            self.parent._inputs = li


class _SelectionEventHandler(ac.SelectionEventHandler):  # type: ignore
    def __init__(self, parent: 'CommandHandlerBase', method_name: str):
        super().__init__()
        self.parent = parent
        self.method_name = method_name

    @catch_exception
    def notify(self, args):
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
        except Exception as e:
            get_context().ui.messageBox(f'Unhandled exception:\n{str(e)}')
        finally:
            self.parent._inputs = li


class _ValidateEventHandler(ac.ValidateInputsEventHandler):  # type: ignore
    def __init__(self, parent: 'CommandHandlerBase'):
        super().__init__()
        self.parent = parent

    @catch_exception
    def notify(self, args):
        event_args = ac.ValidateInputsEventArgs.cast(args)
        inputs = event_args.inputs
        li = self.parent._inputs
        try:
            self.parent._inputs = inputs
            self.parent.notify_validate(event_args)
        except Exception as e:
            get_context().ui.messageBox(f'Unhandled exception:\n{str(e)}')
        finally:
            self.parent._inputs = li


class CommandHandlerBase(ac.CommandCreatedEventHandler):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self._inputs: ty.Optional[ac.CommandInputs] = None
        self.run_execute: bool

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
            raise Exception('CommandInputs is not available here.')
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
        self.run_execute = True
        try:
            self.notify_create(event_args)
        except Exception as e:
            get_context().ui.messageBox(f'Unhandled exception:\n{str(e)}')
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
            _ = inputs.addBoolValueInput(INP_ID_PARTS_DATA_PATH_BOOL, 'Parts Data Dir', False)
        _ = inputs.addDropDownCommandInput(INP_ID_CAP_DESC_DD, 'Cap', ac.DropDownStyles.TextListDropDownStyle)
        _ = inputs.addDropDownCommandInput(INP_ID_STABILIZER_DESC_DD, 'Stabilizer', ac.DropDownStyles.TextListDropDownStyle)
        _ = inputs.addDropDownCommandInput(INP_ID_STABILIZER_ORIENTATION_DD, 'Stabilizer Orientation', ac.DropDownStyles.TextListDropDownStyle)
        _ = inputs.addDropDownCommandInput(INP_ID_SWITCH_DESC_DD, 'Switch', ac.DropDownStyles.TextListDropDownStyle)
        _ = inputs.addDropDownCommandInput(INP_ID_SWITCH_ORIENTATION_DD, 'Switch Orientation', ac.DropDownStyles.TextListDropDownStyle)
        _ = inputs.addDropDownCommandInput(INP_ID_KEY_V_ALIGN_TO_DD, 'Key V-Align', ac.DropDownStyles.TextListDropDownStyle)
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
            fd.title = 'Choose Parts Info Dir'
            if fd.showDialog() != ac.DialogResults.DialogOK:
                return
            path = pathlib.Path(fd.folder)
            try:
                self.set_parts_data_path(path)
            except Exception:
                con.ui.messageBox('The directory is not Parts Info dir.')

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
    def __init__(self, inp: SelectionCommandInput, attr_name: str, entity_class: ty.Type[ty.Union[af.BRepBody, af.ConstructionPlane]]) -> None:
        self.inp = inp
        self.attr_name = attr_name
        self.cls = entity_class
    
    def get_locators_attr_value(self, selected_locators: ty.List[F3Occurrence]) -> ty.Optional[str]:
        v: ty.Optional[str] = ''
        for ent in selected_locators:
            if self.attr_name not in ent.comp_attr:
                raise Exception('This file is corrupted.')
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
            con = get_context()
            ent = self.cls.cast(con.find_by_token(token)[0])
            if not has_sel_in(self.inp):
                self.inp.addSelection(ent)
            else:
                current_ent = self.cls.cast(self.inp.selection(0).entity)
                if current_ent != ent:
                    self.inp.clearSelection()
                    self.inp.addSelection(ent)
            self.inp.tooltip = ent.name


def get_selected_locators(locator_in: ac.SelectionCommandInput):
    locs = [af.Occurrence.cast(locator_in.selection(i).entity) for i in range(locator_in.selectionCount)]
    return list([F3Occurrence(o) for o in filter(lambda x: x is not None, locs)])


def locator_notify_pre_select(inp_id: str, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection):
    con = get_context()
    e = af.Occurrence.cast(selection.entity)
    if e is None:
        event_args.isSelectable = False
        return
    ent = F3Occurrence(e)
    if (not ent.has_parent) or ent.parent.name != CN_KEY_LOCATORS:
        event_args.isSelectable = False
        return
    lp_ci = InputLocators(active_input, AN_LOCATORS_PLANE_TOKEN, af.ConstructionPlane)
    preselect_lp_token = lp_ci.get_locators_attr_value([ent])
    if preselect_lp_token is None:
        raise Exception('Internal Error: Key locator lacks lp_token.')
    preselect_lp = con.find_by_token(preselect_lp_token)[0]
    locator_in = get_ci(active_input.commandInputs, inp_id, ac.SelectionCommandInput)
    if has_sel_in(locator_in):
        selected_lp_token = lp_ci.get_locators_attr_value(get_selected_locators(locator_in))
        if selected_lp_token is not None and len(selected_lp_token) > 0:
            selected_lp = con.find_by_token(selected_lp_token)[0]
            if preselect_lp != selected_lp:
                event_args.isSelectable = False


def _check_key_placeholders(selected_kpns: ty.Set[str], category_enables: ty.Dict[str, bool]) -> ty.Optional[ty.Tuple[ty.List[af.BRepBody], ty.List[af.BRepBody], ty.List[af.BRepBody], ty.Set[str], ty.List[ty.Tuple[af.BRepBody, af.BRepBody]]]]:
    con = get_context()
    inl_occ = con.child[CN_INTERNAL]
    locators_occ = inl_occ.child[CN_KEY_LOCATORS]
    using_ka_names: ty.Set[str] = set()
    for _, kl_occ in locators_occ.child.items():
        specifier = kl_occ.comp_attr[AN_LOCATORS_SPECIFIER]
        options = [kl_occ.comp_attr[an] for an in ANS_OPTION]
        using_ka_names.add(key_assembly_name(specifier, *options))

    def _get_attr_value(body: af.BRepBody, attr_name: str):
        a = body.attributes.itemByName(ATTR_GROUP, attr_name)
        if a is None:
            raise Exception('Bad code.')
        return a.value

    AN_PART_NAME = 'part_name'
    AN_KP_NAME = 'kp_name'
    AN_BODY_NAME = 'body_name'
    AN_CATEGORY_NAME = 'category_name'
    AN_LR = 'left_right'
    AV_LEFT = 'left'
    AV_RIGHT = 'right'
    CN_TEMP = 'temp' + MAGIC
    temp_occ = inl_occ.child.get_real(CN_TEMP)
    temp_occ.light_bulb = True
    cache_temp_body: ty.List[ty.Tuple[af.BRepBody, af.BRepBody]] = []

    def _get_temp_body(orig_body: af.BRepBody, part_name: str, attrs: ty.List[ty.Tuple[str, str]]):
        for ob, tb in cache_temp_body:
            if ob == orig_body:
                return tb
        tb = orig_body.copyToComponent(temp_occ.raw_occ)
        attrs.append((AN_BODY_NAME, orig_body.name))
        attrs.append((AN_PART_NAME, part_name))
        for n, v in attrs:
            tb.nativeObject.attributes.add(ATTR_GROUP, n, v)
        cache_temp_body.append((orig_body, tb))
        return tb

    col = CreateObjectCollectionT(af.BRepBody)
    key_placeholders_occ = inl_occ.child[CN_KEY_PLACEHOLDERS]
    for kpn, kp_occ in key_placeholders_occ.child.items():
        for n, c_kp_occ in kp_occ.child.items():
            if n.endswith(CNP_KEY_ASSEMBLY):
                for pn, part_occ in c_kp_occ.child.items():
                    cb = part_occ.bodies_by_attr(AN_TERRITORY)[0]
                    col.add(_get_temp_body(cb, pn, [(AN_KP_NAME, kpn)]))
    
    if len(col) < 2:
        for _, tb in cache_temp_body:
            tb.deleteMe()
        return

    inf_in = con.des.createInterferenceInput(col)
    inf_results = con.des.analyzeInterference(inf_in)

    def _get_names(entity):
        brep = af.BRepBody.cast(entity)
        return _get_attr_value(brep, AN_KP_NAME), _get_attr_value(brep, AN_PART_NAME)

    def _get_part_occ(kpn: str, pn: str):
        for n, c_kp_occ in key_placeholders_occ.child[kpn].child.items():
            if n.endswith(CNP_KEY_ASSEMBLY):
                return c_kp_occ.child[pn]
        raise Exception('Bad code.')

    def _check_mev_mev(left_part_occ: VirtualF3Occurrence, right_part_occ: VirtualF3Occurrence):
        col.clear()
        for po, lr in zip([left_part_occ, right_part_occ], [AV_LEFT, AV_RIGHT]):
            for b in po.bodies_by_attr(AN_MEV):
                col.add(_get_temp_body(b, po.name, [(AN_LR, lr)]))
        if len(col) < 2:
            return []
        inf_in = con.des.createInterferenceInput(col)
        inf_results = con.des.analyzeInterference(inf_in)
        if inf_results is None:
            con.ui.messageBox('You came across a bug of Fusion 360. The interference check is invalid about MEV - MEV.\nAbout the bug:\nhttps://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251')
            return []
        return list(inf_results)

    def _check_mf_hole(left_part_occ: VirtualF3Occurrence, right_part_occ: VirtualF3Occurrence):
        ret: ty.List[af.InterferenceResult] = []
        for hole in right_part_occ.bodies_by_attr(AN_HOLE):
            col.clear()
            col.add(_get_temp_body(hole, right_part_occ.name, [(AN_LR, AV_RIGHT), (AN_CATEGORY_NAME, AN_HOLE)]))
            for mf in left_part_occ.bodies_by_attr(AN_MF):
                col.add(_get_temp_body(mf, left_part_occ.name, [(AN_LR, AV_LEFT), (AN_CATEGORY_NAME, AN_MF)]))
            if len(col) < 2:
                continue
            inf_in = con.des.createInterferenceInput(col)
            inf_results = con.des.analyzeInterference(inf_in)
            if inf_results is None:
                con.ui.messageBox('You came across a bug of Fusion 360. The interference check is invalid about MF - Hole.\nAbout the bug:\nhttps://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251')
                continue
            ret.extend(inf_results)
        return ret

    def _get_lb_rb(ir: af.InterferenceResult):
        xb = af.BRepBody.cast(ir.entityOne)
        yb = af.BRepBody.cast(ir.entityTwo)
        return (xb, yb) if _get_attr_value(xb, AN_LR) == AV_LEFT else (yb, xb)

    hit_mev: ty.List[af.BRepBody] = []
    hit_hole: ty.List[af.BRepBody] = []
    hit_mf: ty.List[af.BRepBody] = []
    hit_kpns: ty.Set[str] = set()

    if inf_results is None:
        con.ui.messageBox('You came across a bug of Fusion 360. Cannot check interference in this geometry.\nAbout the bug:\nhttps://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251')
        return hit_mev, hit_hole, hit_mf, hit_kpns, cache_temp_body

    for ir in inf_results:
        left_kpn, left_pn = _get_names(ir.entityOne)
        right_kpn, right_pn = _get_names(ir.entityTwo)
        if left_kpn not in selected_kpns and right_kpn not in selected_kpns:
            continue
        if left_kpn != right_kpn:
            left_part_occ = _get_part_occ(left_kpn, left_pn)
            right_part_occ = _get_part_occ(right_kpn, right_pn)
            hit = False
            if category_enables[AN_MEV]:
                for ir in _check_mev_mev(left_part_occ, right_part_occ):
                    hit = True
                    hit_mev.extend(_get_lb_rb(ir))
            if category_enables[AN_MF] or category_enables[AN_HOLE]:
                for ir in _check_mf_hole(left_part_occ, right_part_occ) + _check_mf_hole(right_part_occ, left_part_occ):
                    hit = True
                    lb, rb = _get_lb_rb(ir)
                    if category_enables[AN_MF]:
                        hit_mf.append(lb)
                    if _get_attr_value(rb, AN_CATEGORY_NAME) != AN_HOLE:
                        rpn = _get_attr_value(rb, AN_PART_NAME)[:len(CNP_PARTS)]
                        raise Exception(f'The part data is corrupted. Two MF bodies are interferencing. The part name: {rpn}')
                    if category_enables[AN_HOLE]:
                        hit_hole.append(rb)
            if hit:
                hit_kpns.add(left_kpn)
                hit_kpns.add(right_kpn)

    return hit_mev, hit_hole, hit_mf, hit_kpns, cache_temp_body


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

    def b_notify_execute_preview(self, selected_locators: ty.List[F3Occurrence] = []) -> ty.Optional[ty.Tuple[ty.List[af.BRepBody], ty.List[af.BRepBody], ty.List[af.BRepBody], ty.Set[str], ty.List[ty.Tuple[af.BRepBody, af.BRepBody]]]]:
        if len(selected_locators) == 0:
            return None
        checkbox_ins = self.get_checkbox_ins()
        if (not checkbox_ins[0].value) or (not any(ci.value for ci in checkbox_ins[1:])):
            return None
        selected_kpns: ty.Set[str] = set()
        for kl_occ in selected_locators:
            pattern_name = kl_occ.comp_attr[AN_LOCATORS_PATTERN_NAME]
            i = int(kl_occ.comp_attr[AN_LOCATORS_I])
            selected_kpns.add(key_placeholder_name(i, pattern_name))
        result = self.check_key_placeholders(selected_kpns)
        if result is None:
            return None
        hit_mev, hit_hole, hit_mf, hit_kpns, cache_temp_body = result

        con = get_context()
        inl_occ = con.child[CN_INTERNAL]
        key_placeholders_occ = inl_occ.child[CN_KEY_PLACEHOLDERS]
        for kpn in hit_kpns:
            key_placeholders_occ.child[kpn].light_bulb = False
            key_placeholders_occ.child[kpn].light_bulb = False

        category_appearance = get_category_appearance()
        for hit_bodies, category in zip([hit_mev, hit_hole, hit_mf], [AN_MEV, AN_HOLE, AN_MF]):
            new_list: ty.List[af.BRepBody] = []
            for b in hit_bodies:
                if b in new_list:
                    continue
                new_list.append(b)
                b.isLightBulbOn = True
                b.appearance = category_appearance[category]

        return result

    def check_key_placeholders(self, selected_kpns: ty.Set[str]) -> ty.Optional[ty.Tuple[ty.List[af.BRepBody], ty.List[af.BRepBody], ty.List[af.BRepBody], ty.Set[str], ty.List[ty.Tuple[af.BRepBody, af.BRepBody]]]]:
        category_enables: ty.Dict[str, bool] = {
            cn: inp.value
            for cn, inp in zip([AN_HOLE, AN_MF, AN_MEV], self.get_checkbox_ins()[1:])
        }
        return _check_key_placeholders(selected_kpns, category_enables)


class MoveComponentCommandBlock:
    def __init__(self, parent: CommandHandlerBase) -> None:
        self.transaction_trans: ty.Optional[ac.Matrix3D] = None
        self.parent = parent

    def show_hide_ins(self, inps_id: ty.List[str], is_show: bool):
        for inp_id in inps_id:
            inp = self.parent.inputs.itemById(inp_id)
            if inp is None:
                raise Exception(f"{inp_id} didn't find in inputs.")
            inp.isEnabled = is_show
            inp.isVisible = is_show
            if not is_show:
                inp.value = 0.  # type: ignore

    def get_inputs(self):
        inputs = self.parent.inputs
        angle_in = ac.AngleValueCommandInput.cast(inputs.itemById(INP_ID_ROTATION_AV))
        x_in = ac.DistanceValueCommandInput.cast(inputs.itemById(INP_ID_X_DV))
        y_in = ac.DistanceValueCommandInput.cast(inputs.itemById(INP_ID_Y_DV))
        return angle_in, x_in, y_in

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

        angle_in, x_in, y_in = self.get_inputs()
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
        v.transformBy(self.transaction_trans)
        mov = ac.Matrix3D.create()
        mov.setCell(0, 3, v.x)
        mov.setCell(1, 3, v.y)
        mov.setCell(2, 3, v.z)
        return mov

    def get_rot_mov_trans(self):
        angle_input, x_input, y_input = self.get_inputs()
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
        raise Exception('Layout Plane cannot be parallel to Z axis.')
    return cp_plane


def get_category_appearance():
    depot_appearance_occ = get_context().child[CN_INTERNAL].child[CN_DEPOT_APPEARANCE]
    category_appearance: ty.Dict[str, ac.Appearance] = {}
    for category, bn in zip([AN_HOLE, AN_MF, AN_MEV], [BN_APPEARANCE_HOLE, BN_APPEARANCE_MF, BN_APPEARANCE_MEV]):
        cat_b = depot_appearance_occ.raw_occ.bRepBodies.itemByName(bn)
        if cat_b is None:
            raise Exception(f'appearance.f3d is corruputed. It lacks {bn} body.')
        category_appearance[category] = cat_b.appearance
    return category_appearance
