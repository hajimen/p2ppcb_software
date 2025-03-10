from operator import attrgetter
import typing as ty
import pickle
import base64
import pathlib
import time
from p2ppcb_composer.cmd_key_common import AN_LOCATORS_SKELETON_TOKEN
from pint import Quantity
import adsk
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput, SelectionEventArgs, SelectionCommandInput, Selection
from f360_common import AN_FILL, AN_HOLE, AN_LOCATORS_ENABLED, AN_LOCATORS_I, AN_LOCATORS_PATTERN_NAME, AV_FLIP, AV_RIGHT, CN_DEPOT_PARTS, CN_FOOT, CN_FOOT_PLACEHOLDERS, CN_KEY_LOCATORS, CN_MISC_PLACEHOLDERS, \
    CNP_KEY_ASSEMBLY, CN_KEY_PLACEHOLDERS, MAGIC, FLOOR_CLEARANCE, ORIGIN_P3D, XU_V3D, YU_V3D, ZU_V3D, BadCodeException, BadConditionException, BodyFinder, CreateObjectCollectionT, F3Occurrence, \
    VirtualF3Occurrence, capture_position, get_context, CN_INTERNAL, AN_PLACEHOLDER, key_placeholder_name, CURRENT_DIR, create_component, CNP_PARTS, EYE_M3D
from p2ppcb_composer.cmd_common import AN_MB_LOCATION_INPUTS, CheckInterferenceCommandBlock, MoveComponentCommandBlock, CommandHandlerBase, get_ci, has_sel_in, load_mb_location_inputs
from route.route import get_cn_mainboard

INP_ID_GENERATE_BRIDGE_BOOL = 'generateBridge'
INP_ID_BRIDGE_PROFILE_SEL = 'bridgeProfile'
INP_ID_MAINBOARD_LAYOUT_RADIO = 'mainboardLayout'
INP_ID_FLIP_BOOL = 'flip'
INP_ID_FOOT_LOCATOR_SEL = 'footLocator'
INP_ID_OFFSET_STR = 'offset'
INP_ID_NUM_FOOT_RADIO = 'numFoot'
INP_ID_FRAME_BODY_SEL = 'frameBody'
INP_ID_MISC_TRIAD = 'miscTriad'

TOOLTIPS_GENERATE_BRIDGE = ('Generate Bridge', 'Generates a bridge body which connects the key/PCB mounts.')

BN_FRAME = 'Frame' + MAGIC
BN_FOOT_BOSS = 'Foot Boss' + MAGIC
BN_MAINBOARD_BOSS = 'Mainboard Boss' + MAGIC
# CPN: Construction Plane Name
CPN_FLOOR = 'Floor' + MAGIC
CNP_FOOT_LOCATORS = '_FL'

AN_FOOT_OFFSET = 'footOffset'

CHIPPING_BODY_THRESHOLD = 10. * (0.1 ** 3)  # 10 mm^3


class OffsetCommandBlock:
    def __init__(self, parent: CommandHandlerBase) -> None:
        super().__init__()
        self.parent = parent

    def get_in(self):
        return ac.StringValueCommandInput.cast(self.parent.inputs.itemById(INP_ID_OFFSET_STR))

    def is_valid(self):
        o_in = self.get_in()
        try:
            if not Quantity(o_in.value).check('mm'):  # type: ignore
                return False
        except:  # noqa: E722
            return False
        return True

    def show(self, visible: bool):
        self.get_in().isVisible = visible

    def get_value(self) -> float:
        o_in = self.get_in()
        return Quantity(o_in.value).m_as('cm')  # type: ignore

    def b_notify_create(self, name: str, initial: str):
        return self.parent.inputs.addStringValueInput(INP_ID_OFFSET_STR, name, initial)
    
    def b_notify_validate(self, event_args: ac.ValidateInputsEventArgs):
        valid = self.is_valid()
        if not valid:
            self.get_in().isValueError = True
        event_args.areInputsValid = valid
        return valid


def collect_body_from_key(an: str):
    con = get_context()
    ret = CreateObjectCollectionT(af.BRepBody)
    inl_occ = con.child[CN_INTERNAL]
    inl_lb = inl_occ.light_bulb
    inl_occ.light_bulb = True
    key_placeholders_occ = inl_occ.child[CN_KEY_PLACEHOLDERS]
    kp_lb = key_placeholders_occ.light_bulb
    key_placeholders_occ.light_bulb = True
    body_finder = BodyFinder()
    for kp_occ in key_placeholders_occ.child.values():
        if not kp_occ.light_bulb:
            continue
        for n, o in kp_occ.child.items():
            if n.endswith(CNP_KEY_ASSEMBLY):
                for p in o.child.values():
                    for b in body_finder.get(p, an):
                        ret.add(b)
    inl_occ.light_bulb = inl_lb
    key_placeholders_occ.light_bulb = kp_lb

    if ret.count == 0:
        raise BadConditionException(f'The design lacks {an} body in the parts.')

    return ret


def fill_frame(is_generate_bridge: bool, profs: ty.List[af.Profile], before_frame_bodies: ty.List[af.BRepBody], offset: float):
    con = get_context()

    def pb_show():
        con.ui.progressBar.show('Filling Frame...', 0, 1, True)
    
    pb_show()

    for b in con.comp.bRepBodies:
        if b.name.startswith(BN_FRAME):
            b.deleteMe()
    pb_show()

    combines = con.root_comp.features.combineFeatures
    thicken_fs = con.comp.features.thickenFeatures
    col = CreateObjectCollectionT(af.BRepFace)
    ss_bodies: ty.List[af.BRepBody] = []
    if is_generate_bridge:
        if len(profs) == 0:
            raise BadConditionException('profs should have a profile at least.')

        extrudes = con.root_comp.features.extrudeFeatures
        col2 = CreateObjectCollectionT(af.BRepBody)
        for prof in profs:
            ex_in = extrudes.createInput(prof, af.FeatureOperations.NewBodyFeatureOperation)
            ex_in.isSolid = True
            ex_in.setSymmetricExtent(ac.ValueInput.createByString('1 m'), False)
            ex = extrudes.add(ex_in)
            col2.add(ex.bodies[0])

        before_bridge_bodies = [b for b in con.comp.bRepBodies if b.isSolid]

        for st in set([a.value for a in con.find_attrs(AN_LOCATORS_SKELETON_TOKEN)]):
            sss = con.find_by_token(st)
            if len(sss) == 0:
                raise BadConditionException('The skeleton surface has been deleted after it was specified.')
            skeleton_surface = af.BRepBody.cast(sss[0])
            col.clear()
            for f in skeleton_surface.faces:
                col.add(f)
            thicken_inp = thicken_fs.createInput(col, ac.ValueInput.createByReal(-(0.3 + offset)), False, af.FeatureOperations.NewBodyFeatureOperation, False)
            tf = thicken_fs.add(thicken_inp)
            pb_show()

            if offset > 0.:
                thicken_inp2 = thicken_fs.createInput(col, ac.ValueInput.createByReal(-offset), False, af.FeatureOperations.NewBodyFeatureOperation, False)
                tf2 = thicken_fs.add(thicken_inp2)
                pb_show()
                col3 = CreateObjectCollectionT(af.BRepBody)
                col3.add(tf2.bodies[0])
                co_in2 = combines.createInput(tf.bodies[0], col3)
                co_in2.operation = af.FeatureOperations.CutFeatureOperation
                co_in2.isKeepToolBodies = False
                _ = combines.add(co_in2)
                pb_show()

            co_in = combines.createInput(tf.bodies[0], col2)
            co_in.operation = af.FeatureOperations.IntersectFeatureOperation
            co_in.isKeepToolBodies = True
            _ = combines.add(co_in)
            pb_show()

        after_bridge_bodies = [b for b in con.comp.bRepBodies if b.isSolid]
        for b in after_bridge_bodies:
            if b not in before_bridge_bodies:
                ss_bodies.append(b)
        
        for b in list(col2):
            b.deleteMe()
        pb_show()

    if is_generate_bridge:
        if len(ss_bodies) == 0:
            raise BadConditionException('Cannot generate a bridge.')

    fill_body_col = collect_body_from_key(AN_FILL)
    if fill_body_col.count == 0:
        raise BadConditionException('There is no key.')

    if is_generate_bridge:
        base_body = ss_bodies.pop(0)
        for b in ss_bodies:
            fill_body_col.add(b)
    else:
        base_body = fill_body_col[0].copyToComponent(con.comp)
        pb_show()
        fill_body_col.removeByIndex(0)
        base_body.isLightBulbOn = True

    if fill_body_col.count > 0:
        co_in3 = combines.createInput(base_body, fill_body_col)
        co_in3.operation = af.FeatureOperations.JoinFeatureOperation
        co_in3.isKeepToolBodies = True
        _ = combines.add(co_in3)
        pb_show()

    fbs: ty.List[af.BRepBody] = []
    for b in con.comp.bRepBodies:
        if not b.isSolid:
            continue
        if b.volume < CHIPPING_BODY_THRESHOLD:  # Chippings often occurs and should be ignored.
            b.deleteMe()
            continue
        if b not in before_frame_bodies:
            fbs.append(b)
    pb_show()

    if len(fbs) == 0:
        raise BadCodeException('Bad code or bad parts data.')
    elif len(fbs) == 1:
        frame_body = fbs[0]
        frame_body.name = BN_FRAME
    else:
        con.ui.messageBox('Separated frames has been generated.')
        fbs = sorted(fbs, key=attrgetter('volume'), reverse=True)
        for i, b in enumerate(fbs):
            b.name = BN_FRAME + f' {i}'

    def get_minpoint(xyz: str):
        return min(fbs, key=attrgetter('boundingBox.minPoint.' + xyz)).boundingBox.minPoint

    def get_maxpoint(xyz: str):
        return max(fbs, key=attrgetter('boundingBox.maxPoint.' + xyz)).boundingBox.maxPoint

    planes = con.comp.constructionPlanes
    plane_in = planes.createInput()
    plane_z = get_minpoint('z').z - FLOOR_CLEARANCE
    plane_in.setByOffset(con.comp.xYConstructionPlane, ac.ValueInput.createByReal(plane_z))

    ifp = planes.itemByName(CPN_FLOOR)
    if ifp is not None:
        ifp.deleteMe()
        pb_show()
    floor_plane = planes.add(plane_in)
    floor_plane.name = CPN_FLOOR
    plane_z = floor_plane.geometry.origin.z  # F360's bug workaround

    min_point_xy = ac.Point3D.create(get_minpoint('x').x, get_minpoint('y').y, plane_z)
    max_point_xy = ac.Point3D.create(get_maxpoint('x').x, get_maxpoint('y').y, plane_z)
    _, min_p = floor_plane.geometry.evaluator.getParameterAtPoint(min_point_xy)
    _, max_p = floor_plane.geometry.evaluator.getParameterAtPoint(max_point_xy)
    floor_plane.displayBounds = ac.BoundingBox2D.create(min_p, max_p)

    con.child[CN_INTERNAL].child[CN_KEY_LOCATORS].light_bulb = False


def get_frame(msg: str = 'Run Fill command first.'):
    frame = get_context().comp.bRepBodies.itemByName(BN_FRAME)
    if frame is None:
        raise BadConditionException(msg)
    return frame


class FillFrameCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.offset_cb: OffsetCommandBlock
        self.check_interference_cb: CheckInterferenceCommandBlock

    @property
    def cmd_name(self) -> str:
        return 'Fill Frame'

    @property
    def tooltip(self) -> str:
        return 'Fills a frame body in the root component. Interference check may require tens of seconds.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/fill'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()

        inl_occ = con.child[CN_INTERNAL]
        inl_occ.light_bulb = True
        disabled_names = set()
        for kl_occ in inl_occ.child[CN_KEY_LOCATORS].child.values():
            if not bool(kl_occ.comp_attr[AN_LOCATORS_ENABLED]):
                pattern_name = kl_occ.comp_attr[AN_LOCATORS_PATTERN_NAME]
                i = int(kl_occ.comp_attr[AN_LOCATORS_I])
                disabled_names.add(key_placeholder_name(i, pattern_name))
        key_placeholders_occ = inl_occ.child[CN_KEY_PLACEHOLDERS]
        key_placeholders_occ.light_bulb = True
        for o in key_placeholders_occ.child.values():
            if not o.light_bulb and o.name not in disabled_names:
                raise BadConditionException('There is unplaced key(s). Please fix it first.')

        bridge_in = self.inputs.addBoolValueInput(INP_ID_GENERATE_BRIDGE_BOOL, 'Generate Bridge', True)
        bridge_in.value = True
        bridge_in.tooltip, bridge_in.tooltipDescription = TOOLTIPS_GENERATE_BRIDGE

        prof_in = self.inputs.addSelectionInput(INP_ID_BRIDGE_PROFILE_SEL, 'Bridge Profile', 'Select profile(s)')
        prof_in.addSelectionFilter('Profiles')
        prof_in.setSelectionLimits(0, 0)

        self.offset_cb = OffsetCommandBlock(self)
        self.offset_cb.b_notify_create('Bridge Offset', '7 mm')
        self.offset_cb.show(False)

        self.check_interference_cb = CheckInterferenceCommandBlock(self)
        self.check_interference_cb.notify_create(event_args)

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        prof_in = self.get_sel_in()
        bridge_in = self.get_bridge_in()
        is_gb = bridge_in.value
        has_sel = has_sel_in(prof_in)
        if changed_input.id == INP_ID_BRIDGE_PROFILE_SEL:
            self.offset_cb.show(has_sel)
        elif changed_input.id == INP_ID_GENERATE_BRIDGE_BOOL:
            prof_in.isVisible = is_gb
            self.offset_cb.show(is_gb)
        self.check_interference_cb.get_checkbox_ins()[0].isVisible = has_sel or (not is_gb)
        self.check_interference_cb.notify_input_changed(event_args, changed_input)

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs) -> None:
        prof_in = self.get_sel_in()
        bridge_in = self.get_bridge_in()
        if has_sel_in(prof_in):
            self.offset_cb.b_notify_validate(event_args)
        elif bridge_in.value:
            event_args.areInputsValid = False

    def get_sel_in(self):
        return get_ci(self.inputs, INP_ID_BRIDGE_PROFILE_SEL, ac.SelectionCommandInput)

    def get_bridge_in(self):
        return get_ci(self.inputs, INP_ID_GENERATE_BRIDGE_BOOL, ac.BoolValueCommandInput)

    def execute_common(self, event_args: CommandEventArgs) -> None:
        sel_in = self.get_sel_in()
        profs = [af.Profile.cast(sel_in.selection(i).entity) for i in range(sel_in.selectionCount)]
        con = get_context()
        before_frame_bodies = [b for b in con.comp.bRepBodies if b.isSolid]
        offset = self.offset_cb.get_value()

        pb = con.ui.progressBar
        try:
            fill_frame(self.get_bridge_in().value, profs, before_frame_bodies, offset)
        finally:
            pb.hide()

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        key_placeholders_occ = get_context().child[CN_INTERNAL].child[CN_KEY_PLACEHOLDERS]
        result = self.check_interference_cb.b_notify_execute_preview([o for o in key_placeholders_occ.child.values() if isinstance(o, F3Occurrence) and o.light_bulb])
        if result is None:
            self.execute_common(event_args)
        else:
            _, _, _, hit_occs, _ = result
            if len(hit_occs) == 0:
                self.execute_common(event_args)

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)


class PlaceMainboardCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.move_comp_cb: MoveComponentCommandBlock
        self.check_interference_cb: CheckInterferenceCommandBlock
        self.offset_cb: OffsetCommandBlock
        self.last_light_bulb = False
        self.flip = False

    @property
    def cmd_name(self) -> str:
        return 'Place Mainboard'

    @property
    def tooltip(self) -> str:
        return 'Places a mainboard. This command places bosses to fix the mainboard in the root component. You should bridge the bosses to the frame manually. Interference check may require tens of seconds.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/place_mainboard'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()

        get_frame()  # check

        self.move_comp_cb = MoveComponentCommandBlock(self)
        self.move_comp_cb.notify_create(event_args)

        self.offset_cb = OffsetCommandBlock(self)
        self.offset_cb.b_notify_create('Offset', '2 mm')

        layout_in = self.inputs.addRadioButtonGroupCommandInput(INP_ID_MAINBOARD_LAYOUT_RADIO, 'Layout')
        layout_in.listItems.add('Back', True)
        layout_in.listItems.add('Bottom', False)

        flip_in = self.inputs.addBoolValueInput(INP_ID_FLIP_BOOL, 'Flip', True)

        self.check_interference_cb = CheckInterferenceCommandBlock(self)
        self.check_interference_cb.notify_create(event_args)
        if_in = self.check_interference_cb.get_checkbox_ins()[0]
        if_in.isVisible = True

        inl_occ = con.child[CN_INTERNAL]
        inl_occ.light_bulb = True
        mp_occ = inl_occ.child.get_real(CN_MISC_PLACEHOLDERS)
        self.last_light_bulb = mp_occ.light_bulb
        mp_occ.light_bulb = True
        cn_mainboard = get_cn_mainboard()
        if cn_mainboard in mp_occ.child:
            o = mp_occ.child[cn_mainboard]
            if AN_MB_LOCATION_INPUTS in o.comp_attr:
                locs = load_mb_location_inputs(o)
                for ci, v in zip(self.move_comp_cb.get_inputs(), locs[0]):
                    ci.value = v
                self.offset_cb.get_in().value = f'{locs[1] * 10} mm'
                for li in list(layout_in.listItems):
                    if li.name == locs[2]:
                        li.isSelected = True
                        break
                flip_in.value = locs[3]
                self.flip = locs[3]
            else:
                flip_in.value = False
                self.flip = False
            self.move_comp_cb.start_transaction(self.get_mainboard_transform())
        else:
            t = self.get_mainboard_transform()
            self.move_comp_cb.start_transaction(t)
            mb_occ = inl_occ.child[CN_DEPOT_PARTS].child[cn_mainboard]
            o = mp_occ.child.add(mb_occ, t)
            o.light_bulb = False
            flip_in.value = False
            self.flip = False

    def get_layout_in(self):
        return get_ci(self.inputs, INP_ID_MAINBOARD_LAYOUT_RADIO, ac.RadioButtonGroupCommandInput)

    def get_flip_in(self):
        return get_ci(self.inputs, INP_ID_FLIP_BOOL, ac.BoolValueCommandInput)

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs) -> None:
        self.offset_cb.b_notify_validate(event_args)

    def get_mainboard_transform(self):
        con = get_context()
        cn_mainboard = get_cn_mainboard()
        mb_occ = con.child[CN_INTERNAL].child[CN_DEPOT_PARTS].child[cn_mainboard]
        mb_bb = mb_occ.comp.boundingBox  # type: ignore
        frame_bb = get_frame().boundingBox
        offset = self.offset_cb.get_value()

        t = ac.Matrix3D.create()
        layout = self.get_layout_in().selectedItem.name
        flip = self.get_flip_in().value
        if layout == 'Back':
            o = ac.Point3D.create(frame_bb.minPoint.x - mb_bb.minPoint.x, frame_bb.maxPoint.y + offset, frame_bb.minPoint.z - mb_bb.minPoint.y)
            mxu = XU_V3D.copy()
            myu = YU_V3D.copy()
            if flip:
                myu.scaleBy(-1.)
            else:
                mxu.scaleBy(-1.)
            t.setWithCoordinateSystem(o, mxu, ZU_V3D, myu)
        else:  # Bottom
            mzu = ZU_V3D.copy()
            myu = YU_V3D.copy()
            if not flip:
                mzu.scaleBy(-1.)
                myu.scaleBy(-1.)
            o = ac.Point3D.create(frame_bb.maxPoint.x - mb_bb.maxPoint.x, frame_bb.maxPoint.y + mb_bb.minPoint.y, frame_bb.minPoint.z + offset)
            t.setWithCoordinateSystem(o, XU_V3D, myu, mzu)
        return t

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        if self.offset_cb.is_valid():
            if changed_input.id == INP_ID_MAINBOARD_LAYOUT_RADIO:
                self.offset_cb.get_in().value = '2 mm'
                t = self.get_mainboard_transform()
                self.move_comp_cb.start_transaction(t)
            elif changed_input.id == INP_ID_OFFSET_STR or changed_input.id == INP_ID_FLIP_BOOL:
                t = self.get_mainboard_transform()
                self.move_comp_cb.start_transaction(t)
            self.move_comp_cb.b_notify_changed_input(changed_input)
        self.check_interference_cb.notify_input_changed(event_args, changed_input)

    def execute_common(self, event_args: CommandEventArgs):
        con = get_context()
        o = con.child[CN_INTERNAL].child[CN_MISC_PLACEHOLDERS].child.get_real(get_cn_mainboard())
        o.transform = self.get_mainboard_transform()
        o.light_bulb = True
        self.move_comp_cb.b_notify_execute_preview(event_args, [o])
        return o

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        o = self.execute_common(event_args)

        if_in = self.check_interference_cb.get_checkbox_ins()[0]
        if if_in.value:
            self.check_interference_cb.b_notify_execute_preview([o], AV_FLIP if self.get_flip_in().value else AV_RIGHT)

        for b in list(con.comp.bRepBodies):
            if b.name.startswith(BN_MAINBOARD_BOSS):
                b.isLightBulbOn = False

        body_finder = BodyFinder()
        for b in body_finder.get(o, AN_FILL, AN_FILL) + body_finder.get(o, AN_FILL, AV_FLIP if self.get_flip_in().value else AV_RIGHT):
            b.isLightBulbOn = True

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        inl_occ = con.child[CN_INTERNAL]

        o = self.execute_common(event_args)
        capture_position()
        o.comp_attr[AN_MB_LOCATION_INPUTS] = base64.b64encode(pickle.dumps([
            [ci.value for ci in self.move_comp_cb.get_inputs()],
            self.offset_cb.get_value(),
            self.get_layout_in().selectedItem.name,
            self.get_flip_in().value,
        ])).decode()
        self.flip = self.get_flip_in().value

        for b in list(con.comp.bRepBodies):
            if b.name.startswith(BN_MAINBOARD_BOSS):
                b.deleteMe()

        if CN_MISC_PLACEHOLDERS in inl_occ.child:
            mp_occ = inl_occ.child[CN_MISC_PLACEHOLDERS]
            body_finder = BodyFinder()
            for b in body_finder.get(o, AN_FILL, AN_FILL) + body_finder.get(o, AN_FILL, AV_FLIP if self.flip else AV_RIGHT):
                b.isLightBulbOn = False
                nb = b.copyToComponent(con.comp)
                nb.isLightBulbOn = True
                nb.name = BN_MAINBOARD_BOSS
            mp_occ.light_bulb = self.last_light_bulb


FOOT_NAMES = [f'Foot {s}{CNP_FOOT_LOCATORS}' for s in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']]


class PlaceFootCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.move_comp_cb: MoveComponentCommandBlock
        self.offset_cb: OffsetCommandBlock
        self.check_interference_cb: CheckInterferenceCommandBlock
        self.last_light_bulb = False
        self.last_num_foot = 0

    @property
    def cmd_name(self) -> str:
        return 'Place Foot'

    @property
    def tooltip(self) -> str:
        return 'Places feet. This command places bosses to fix the feet in the root component. You should bridge the bosses to the frame manually. Interference check may require tens of seconds.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/place_foot'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()

        get_frame()  # check

        inl_occ = con.child[CN_INTERNAL]
        inl_occ.light_bulb = True
        fp_occ = inl_occ.child.get_real(CN_FOOT_PLACEHOLDERS)
        self.last_light_bulb = fp_occ.light_bulb
        fp_occ.light_bulb = True
        f_occ = inl_occ.child[CN_DEPOT_PARTS].child[CN_FOOT]
        body_finder = BodyFinder()
        for b in body_finder.get(f_occ, AN_PLACEHOLDER):
            b.isLightBulbOn = False
        for b in body_finder.get(f_occ, AN_FILL):
            b.isLightBulbOn = True
        for fn in FOOT_NAMES:
            if fn not in fp_occ.child:
                o = fp_occ.child.new_real(fn)
                o.light_bulb = True  # F360's bug workaround
                fo = o.child.add(f_occ)
                fo.light_bulb = True
                for b in body_finder.get(fo, AN_PLACEHOLDER):
                    nb = b.copyToComponent(o.raw_occ)
                    nb.name = b.name
                    nb.isLightBulbOn = True
                o.light_bulb = False  # F360's bug workaround

        last_num_foot = 0
        for _, po in fp_occ.child.items():
            if po.light_bulb:
                last_num_foot += 1
        if last_num_foot != 4 and last_num_foot != 6 and last_num_foot != 8:
            last_num_foot = 0
        self.last_num_foot = last_num_foot

        inputs = self.inputs

        nf_in = inputs.addRadioButtonGroupCommandInput(INP_ID_NUM_FOOT_RADIO, 'Num of feet')
        nf_in.listItems.add('4', last_num_foot == 4 or last_num_foot == 0)
        nf_in.listItems.add('6', last_num_foot == 6)
        nf_in.listItems.add('8', last_num_foot == 8)

        locator_in = inputs.addSelectionInput(INP_ID_FOOT_LOCATOR_SEL, 'Foot', 'Select feet to move')
        locator_in.addSelectionFilter('SolidBodies')
        locator_in.setSelectionLimits(0, 0)

        self.move_comp_cb = MoveComponentCommandBlock(self)
        self.move_comp_cb.notify_create(event_args)
        self.offset_cb = OffsetCommandBlock(self)
        self.offset_cb.b_notify_create('Offset', fp_occ.comp_attr[AN_FOOT_OFFSET] if AN_FOOT_OFFSET in fp_occ.comp_attr else '0 mm')

        self.check_interference_cb = CheckInterferenceCommandBlock(self)
        self.check_interference_cb.notify_create(event_args)

    def place_initial(self, floor: float, num_foot: int):
        con = get_context()
        inl_occ = con.child[CN_INTERNAL]
        fp_occ = inl_occ.child.get_real(CN_FOOT_PLACEHOLDERS)

        fb = get_frame().boundingBox
        locs: ty.List[ty.Tuple[float, float]]
        if num_foot == 4:
            locs = [(fb.minPoint.x, fb.maxPoint.y), (fb.maxPoint.x, fb.maxPoint.y), (fb.minPoint.x, fb.minPoint.y), (fb.maxPoint.x, fb.minPoint.y), ]
        elif num_foot == 6:
            locs = [(fb.minPoint.x, fb.maxPoint.y), ((fb.minPoint.x + fb.maxPoint.x) / 2, fb.maxPoint.y), (fb.maxPoint.x, fb.maxPoint.y),
                    (fb.minPoint.x, fb.minPoint.y), ((fb.minPoint.x + fb.maxPoint.x) / 2, fb.minPoint.y), (fb.maxPoint.x, fb.minPoint.y), ]
        elif num_foot == 8:
            xw = (fb.maxPoint.x - fb.minPoint.x) / 3
            min_x = fb.minPoint.x
            locs = [(fb.minPoint.x, fb.maxPoint.y), (min_x + xw, fb.maxPoint.y), (min_x + xw * 2, fb.maxPoint.y), (fb.maxPoint.x, fb.maxPoint.y),
                    (fb.minPoint.x, fb.minPoint.y), (min_x + xw, fb.minPoint.y), (min_x + xw * 2, fb.minPoint.y), (fb.maxPoint.x, fb.minPoint.y), ]
        else:
            raise BadCodeException()

        for fn, (x, y), rot in zip(
                FOOT_NAMES[:num_foot],
                locs,
                [False] * (num_foot // 2) + [True] * (num_foot // 2)):
            fo = fp_occ.child[fn]
            t = ac.Matrix3D.create()
            t.setCell(0, 3, x)
            t.setCell(1, 3, y)
            t.setCell(2, 3, floor)
            if rot:
                t.setCell(0, 0, -1.)
                t.setCell(1, 1, -1.)
            fo.transform = t
            fo.light_bulb = True
        for fn in FOOT_NAMES[num_foot:]:
            fo = fp_occ.child[fn]
            fo.light_bulb = False

    def notify_pre_select(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        if active_input.id == INP_ID_FOOT_LOCATOR_SEL:
            e: af.BRepBody = selection.entity  # type: ignore
            if not e.name.startswith('Foot Case'):
                event_args.isSelectable = False
                return
            if e.assemblyContext is None or e.assemblyContext.assemblyContext is None or e.assemblyContext.assemblyContext.component.name != CN_FOOT_PLACEHOLDERS:
                event_args.isSelectable = False
                return

    def get_num_foot_in(self):
        return get_ci(self.inputs, INP_ID_NUM_FOOT_RADIO, ac.RadioButtonGroupCommandInput)

    def get_num_foot(self):
        return int(self.get_num_foot_in().selectedItem.name)

    def get_locator_in(self):
        return get_ci(self.inputs, INP_ID_FOOT_LOCATOR_SEL, ac.SelectionCommandInput)

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs) -> None:
        self.offset_cb.b_notify_validate(event_args)

    def set_manipulator(self):
        locator_in = self.get_locator_in()
        first_sel_body = af.BRepBody.cast(locator_in.selection(0).entity)
        first_sel_occ = F3Occurrence(first_sel_body.assemblyContext)
        orig = ORIGIN_P3D.copy()
        orig.transformBy(first_sel_occ.transform)
        t = ac.Matrix3D.create()
        t.setWithCoordinateSystem(orig, XU_V3D, YU_V3D, ZU_V3D)
        self.move_comp_cb.start_transaction(t)

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        if_in = self.check_interference_cb.get_checkbox_ins()[0]
        locator_in = self.get_locator_in()
        num_foot_in = self.get_num_foot_in()
        if changed_input.id == INP_ID_FOOT_LOCATOR_SEL:
            if has_sel_in(locator_in):
                self.set_manipulator()
                if_in.isVisible = True
                if_in.value = False
                num_foot_in.isVisible = False
            else:
                self.move_comp_cb.stop_transaction()
                if_in.isVisible = False
                if_in.value = False
                num_foot_in.isVisible = True
            self.check_interference_cb.show(if_in.value)
            locator_in.hasFocus = True
        elif changed_input.id == INP_ID_NUM_FOOT_RADIO:
            if self.offset_cb.is_valid():
                self.get_locator_in().clearSelection()
                self.move_comp_cb.stop_transaction()
        self.move_comp_cb.b_notify_changed_input(changed_input)
        self.check_interference_cb.notify_input_changed(event_args, changed_input)

    def execute_common(self, event_args: CommandEventArgs):
        con = get_context()
        locator_in = self.get_locator_in()
        num_foot = self.get_num_foot()
        selected_locators = [F3Occurrence(ty.cast(af.BRepBody, locator_in.selection(i).entity).assemblyContext) for i in range(locator_in.selectionCount)]
        floor_cp = con.comp.constructionPlanes.itemByName(CPN_FLOOR)
        if floor_cp is None:
            raise BadConditionException(f'{CPN_FLOOR} is required. Please run Fill command.')
        floor = floor_cp.geometry.origin.z + self.offset_cb.get_value()
        if self.last_num_foot == num_foot:
            fp_occ = con.child[CN_INTERNAL].child.get_real(CN_FOOT_PLACEHOLDERS)
            for fn in FOOT_NAMES[:num_foot]:
                fo = fp_occ.child[fn]
                t = fo.transform.copy()
                t.setCell(2, 3, floor)
                fo.transform = t
        else:
            self.place_initial(floor, num_foot)
        self.move_comp_cb.b_notify_execute_preview(event_args, selected_locators)
        return selected_locators

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        selected_locators = self.execute_common(event_args)
        for b in list(con.comp.bRepBodies):
            if b.name.startswith(BN_FOOT_BOSS):
                b.isLightBulbOn = False
        body_finder = BodyFinder()
        for o in selected_locators:
            for b in body_finder.get(o, AN_FILL, AN_FILL):
                b.isVisible = True
        self.check_interference_cb.b_notify_execute_preview(selected_locators)

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        inl_occ = con.child[CN_INTERNAL]
        self.execute_common(event_args)
        capture_position()

        for b in list(con.comp.bRepBodies):
            if b.name.startswith(BN_FOOT_BOSS):
                b.deleteMe()

        fp_occ = inl_occ.child[CN_FOOT_PLACEHOLDERS]
        fp_occ.comp_attr[AN_FOOT_OFFSET] = self.offset_cb.get_in().value

        fos = [fp_occ.child[fn].child.get_real(CN_FOOT) for fn in FOOT_NAMES[:self.get_num_foot()]]
        body_finder = BodyFinder()
        for o in fos:
            o.parent.light_bulb = True
            o.light_bulb = True
            for b in body_finder.get(o, AN_FILL):
                nb = b.copyToComponent(con.comp)
                nb.isLightBulbOn = True
                nb.name = BN_FOOT_BOSS
        f_occ = inl_occ.child[CN_DEPOT_PARTS].child[CN_FOOT]
        for b in body_finder.get(f_occ, AN_FILL):
            b.isLightBulbOn = False

        fp_occ.light_bulb = self.last_light_bulb


def hole_all_parts(frame: af.BRepBody):
    con = get_context()

    def pb_show():
        con.ui.progressBar.show('Holing Frame...', 0, 1, True)
    
    pb_show()

    hole_body_col = collect_body_from_key(AN_HOLE)
    other_occs: ty.List[VirtualF3Occurrence] = []
    inl_occ = con.child[CN_INTERNAL]
    if CN_MISC_PLACEHOLDERS in inl_occ.child:
        other_occs.extend(inl_occ.child[CN_MISC_PLACEHOLDERS].child.values())
    inl_occ.light_bulb = True  # F360 bug about isLightBulb workaround
    if CN_FOOT_PLACEHOLDERS in inl_occ.child:
        fp_occ = inl_occ.child[CN_FOOT_PLACEHOLDERS]
        fp_occ.light_bulb = True  # F360 bug about isLightBulb workaround
        for ph_occ in fp_occ.child.values():
            if ph_occ.light_bulb:
                other_occs.append(ph_occ.child[CN_FOOT])
    body_finder = BodyFinder()
    for o in other_occs:
        if AN_MB_LOCATION_INPUTS in o.comp_attr:
            flip = load_mb_location_inputs(o)[3]
            for b in body_finder.get(o, AN_HOLE, AV_FLIP if flip else AV_RIGHT) + body_finder.get(o, AN_HOLE, AN_HOLE):
                hole_body_col.add(b)
        else:
            for b in body_finder.get(o, AN_HOLE):
                hole_body_col.add(b)

    before_frame_bodies = [b for b in con.comp.bRepBodies if b.isSolid]
    frame.name = BN_FRAME
    combines = con.root_comp.features.combineFeatures

    if len(hole_body_col) > 0:
        co_in4 = combines.createInput(frame, hole_body_col)
        co_in4.operation = af.FeatureOperations.CutFeatureOperation
        co_in4.isKeepToolBodies = True
        _ = combines.add(co_in4)
        pb_show()

    after_frame_bodies = [b for b in con.comp.bRepBodies if b.isSolid]
    nbs: ty.List[af.BRepBody] = []
    for b in after_frame_bodies:
        hit = False
        for bb in before_frame_bodies:
            if bb == b:
                hit = True
                break
        if not hit:
            nbs.append(b)
    for b in list(nbs):
        try:
            if b.volume < CHIPPING_BODY_THRESHOLD:
                nbs.remove(b)
        except RuntimeError:  # Sometimes b.volume raises "RuntimeError: 2 : InternalValidationError : ASMInterface::getEntityVolume((ENTITY*)body, res, achieved_precision)"
            pass

    inl_occ.light_bulb = False


class HolePartsCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()

    @property
    def cmd_name(self) -> str:
        return 'Hole'

    @property
    def tooltip(self) -> str:
        return 'Holes all parts, including the mainboard and the feet. You can print the frame body after this command.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/hole'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        frame_in = self.inputs.addSelectionInput(INP_ID_FRAME_BODY_SEL, 'Frame Body', 'Select a body to hole')
        frame_in.addSelectionFilter('SolidBodies')
        frame_in.setSelectionLimits(1, 1)

    def get_frame_in(self):
        return get_ci(self.inputs, INP_ID_FRAME_BODY_SEL, ac.SelectionCommandInput)

    def execute_common(self, event_args: CommandEventArgs):
        frame = af.BRepBody.cast(self.get_frame_in().selection(0).entity)
        pb = get_context().ui.progressBar
        try:
            hole_all_parts(frame)
        finally:
            pb.hide()

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
        event_args.isValidResult = True

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)


class PlaceMiscCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()

    @property
    def cmd_name(self) -> str:
        return 'Place Misc'

    @property
    def tooltip(self) -> str:
        return 'Places miscellaneous F3D file. You should run this command after Fill command and before Hole command.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/place_misc'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()
        file_dlg = con.ui.createFileDialog()
        file_dlg.isMultiSelectEnabled = False
        file_dlg.initialDirectory = str(CURRENT_DIR / 'f3d')
        file_dlg.title = 'Open F3D file'
        file_dlg.filter = 'F3D File (*.f3d)'
        
        if file_dlg.showOpen() != ac.DialogResults.DialogOK:
            self.create_ok = False
            return
        p = file_dlg.filename
        n = pathlib.Path(p).stem

        inl_occ = get_context().child[CN_INTERNAL]
        depot_occ = inl_occ.child.get_real(CN_DEPOT_PARTS)

        if n + CNP_PARTS in depot_occ.child:
            part_occ = depot_occ.child.get_real(n + CNP_PARTS)
        else:
            with create_component(depot_occ.comp, n, CNP_PARTS) as container:
                im = con.app.importManager
                try:
                    im.importToTarget(im.createFusionArchiveImportOptions(p), depot_occ.comp)
                    for _ in range(100):  # F360's bug workaround
                        time.sleep(0.01)
                        adsk.doEvents()
                except Exception:
                    raise BadConditionException(f'F3D file import failed: {p}')
            part_occ = container.pop()
        self.part_occ = part_occ
        self.triad_in = self.inputs.addTriadCommandInput(INP_ID_MISC_TRIAD, EYE_M3D)
        misc_occ = inl_occ.child.get_real(CN_MISC_PLACEHOLDERS)
        if self.part_occ.name in misc_occ.child:
            o = misc_occ.child[self.part_occ.name]
            self.triad_in.transform = o.transform

        self.check_interference_cb = CheckInterferenceCommandBlock(self)
        self.check_interference_cb.notify_create(event_args)
        if_in = self.check_interference_cb.get_checkbox_ins()[0]
        if_in.isVisible = True

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        self.check_interference_cb.notify_input_changed(event_args, changed_input)

    def execute_common(self, event_args: CommandEventArgs):
        inl_occ = get_context().child[CN_INTERNAL]
        misc_occ = inl_occ.child.get_real(CN_MISC_PLACEHOLDERS)
        if self.part_occ.name in misc_occ.child:
            o = misc_occ.child[self.part_occ.name]
        else:
            o = misc_occ.child.add(self.part_occ)
        o.light_bulb = True
        o.transform = self.triad_in.transform
        return o

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        o = self.execute_common(event_args)

        if_in = self.check_interference_cb.get_checkbox_ins()[0]
        if if_in.value:
            self.check_interference_cb.b_notify_execute_preview([ty.cast(F3Occurrence, o)])

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
