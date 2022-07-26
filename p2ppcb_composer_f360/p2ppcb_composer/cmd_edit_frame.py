from operator import attrgetter
import typing as ty
import pickle
import base64
from p2ppcb_composer.cmd_key_common import AN_LOCATORS_SKELETON_TOKEN
from pint import Quantity
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput, SelectionEventArgs, SelectionCommandInput, Selection
from f360_common import AN_FILL, AN_HOLE, AN_LOCATORS_ENABLED, AN_LOCATORS_I, AN_LOCATORS_PATTERN_NAME, AN_MEV, AN_MF, CN_DEPOT_PARTS, CN_FOOT, CN_FOOT_PLACEHOLDERS, CN_KEY_LOCATORS, CN_MISC_PLACEHOLDERS, \
    CNP_KEY_ASSEMBLY, CN_KEY_PLACEHOLDERS, MAGIC, MIN_FLOOR_HEIGHT, ORIGIN_P3D, XU_V3D, YU_V3D, ZU_V3D, BadCodeException, BadConditionException, BodyFinder, CreateObjectCollectionT, F3Occurrence, \
    VirtualF3Occurrence, get_context, CN_INTERNAL, ANS_HOLE_MEV_MF, AN_PLACEHOLDER, key_placeholder_name
from p2ppcb_composer.cmd_common import CheckInterferenceCommandBlock, MoveComponentCommandBlock, CommandHandlerBase, get_ci, has_sel_in, get_category_appearance
from route.route import get_cn_mainboard

INP_ID_GENERATE_BRIDGE_BOOL = 'generateBridge'
INP_ID_BRIDGE_PROFILE_SEL = 'bridgeProfile'
INP_ID_MAINBOARD_LAYOUT_RADIO = 'mainboardLayout'
INP_ID_FLIP_BOOL = 'flip'
INP_ID_CHECK_INTERFERENCE_BOOL = 'checkInterference'
INP_ID_FOOT_LOCATOR_SEL = 'footLocator'
INP_ID_OFFSET_STR = 'offset'
INP_ID_NUM_FOOT_RADIO = 'numFoot'
INP_ID_FRAME_BODY_SEL = 'frameBody'

TOOLTIPS_GENERATE_BRIDGE = ('Generate Bridge', 'Generates a bridge body which connects the key/PCB mounts.')

BN_FRAME = 'Frame' + MAGIC
BN_FOOT_BOSS = 'Foot Boss' + MAGIC
BN_MAINBOARD_BOSS = 'Mainboard Boss' + MAGIC
# CPN: Construction Plane Name
CPN_INTERNAL_FLOOR = 'Internal Floor' + MAGIC
CNP_FOOT_LOCATORS = '_FL'

AN_MB_LOCATION_INPUTS = 'mbLocationInputs'
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
    key_placeholders_occ = con.child[CN_INTERNAL].child[CN_KEY_PLACEHOLDERS]
    body_finder = BodyFinder()
    for kp_occ in key_placeholders_occ.child.values():
        if not kp_occ.light_bulb:
            continue
        for n, o in kp_occ.child.items():
            if n.endswith(CNP_KEY_ASSEMBLY):
                for p in o.child.values():
                    for b in body_finder.get(p, an):
                        rb = b.copyToComponent(con.comp)
                        rb.isLightBulbOn = True
                        ret.add(rb)

    if ret.count == 0:
        raise BadConditionException(f'The design lacks {an} body in the parts.')

    return ret


def fill_frame(is_generate_bridge: bool, profs: ty.List[af.Profile], before_frame_bodies: ty.List[af.BRepBody], offset: float):
    con = get_context()

    for b in con.comp.bRepBodies:
        if b.name.startswith(BN_FRAME):
            b.deleteMe()

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
                raise BadConditionException('Skeleton Surface has been deleted after it was specified.')
            skeleton_surface = af.BRepBody.cast(sss[0])
            col.clear()
            for f in skeleton_surface.faces:
                col.add(f)
            thicken_inp = thicken_fs.createInput(col, ac.ValueInput.createByReal(-(0.3 + offset)), False, af.FeatureOperations.NewBodyFeatureOperation, False)
            tf = thicken_fs.add(thicken_inp)

            if offset > 0.:
                thicken_inp2 = thicken_fs.createInput(col, ac.ValueInput.createByReal(-offset), False, af.FeatureOperations.NewBodyFeatureOperation, False)
                tf2 = thicken_fs.add(thicken_inp2)
                col3 = CreateObjectCollectionT(af.BRepBody)
                col3.add(tf2.bodies[0])
                co_in2 = combines.createInput(tf.bodies[0], col3)
                co_in2.operation = af.FeatureOperations.CutFeatureOperation
                co_in2.isKeepToolBodies = False
                _ = combines.add(co_in2)

            co_in = combines.createInput(tf.bodies[0], col2)
            co_in.operation = af.FeatureOperations.IntersectFeatureOperation
            co_in.isKeepToolBodies = True
            _ = combines.add(co_in)

        after_bridge_bodies = [b for b in con.comp.bRepBodies if b.isSolid]
        for b in after_bridge_bodies:
            if b not in before_bridge_bodies:
                ss_bodies.append(b)
        
        for b in list(col2):
            b.deleteMe()

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
        base_body = fill_body_col[0]
        fill_body_col.removeByIndex(0)

    if fill_body_col.count > 0:
        co_in3 = combines.createInput(base_body, fill_body_col)
        co_in3.operation = af.FeatureOperations.JoinFeatureOperation
        co_in3.isKeepToolBodies = False
        _ = combines.add(co_in3)

    fbs: ty.List[af.BRepBody] = []
    for b in con.comp.bRepBodies:
        if not b.isSolid:
            continue
        if b.volume < CHIPPING_BODY_THRESHOLD:  # Chippings often occurs and should be ignored.
            b.deleteMe()
            continue
        if b not in before_frame_bodies:
            fbs.append(b)

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
    plane_z = get_minpoint('z').z - MIN_FLOOR_HEIGHT
    plane_in.setByOffset(con.comp.xYConstructionPlane, ac.ValueInput.createByReal(plane_z))

    ifp = planes.itemByName(CPN_INTERNAL_FLOOR)
    if ifp is not None:
        ifp.deleteMe()
    floor_plane = planes.add(plane_in)
    floor_plane.name = CPN_INTERNAL_FLOOR
    plane_z = floor_plane.geometry.origin.z  # F360's bug workaround

    min_point_xy = ac.Point3D.create(get_minpoint('x').x, get_minpoint('y').y, plane_z)
    max_point_xy = ac.Point3D.create(get_maxpoint('x').x, get_maxpoint('y').y, plane_z)
    _, min_p = floor_plane.geometry.evaluator.getParameterAtPoint(min_point_xy)
    _, max_p = floor_plane.geometry.evaluator.getParameterAtPoint(max_point_xy)
    floor_plane.displayBounds = ac.BoundingBox2D.create(min_p, max_p)

    con.child[CN_INTERNAL].child[CN_KEY_LOCATORS].light_bulb = False


def get_frame(func: ty.Optional[ty.Callable] = None):
    frame = get_context().comp.bRepBodies.itemByName(BN_FRAME)
    if frame is None:
        raise BadCodeException()
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
                self.run_execute = False
                raise BadConditionException('There is unplaced key(s). Please fix it first.')

        bridge_in = self.inputs.addBoolValueInput(INP_ID_GENERATE_BRIDGE_BOOL, 'Generate Bridge', True)
        bridge_in.value = True
        bridge_in.tooltip, bridge_in.tooltipDescription = TOOLTIPS_GENERATE_BRIDGE

        prof_in = self.inputs.addSelectionInput(INP_ID_BRIDGE_PROFILE_SEL, 'Bridge Profile', 'Select an entity')
        prof_in.addSelectionFilter('Profiles')
        prof_in.setSelectionLimits(0, 0)

        self.offset_cb = OffsetCommandBlock(self)
        self.offset_cb.b_notify_create('Bridge Offset', '5 mm')
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

        fill_frame(self.get_bridge_in().value, profs, before_frame_bodies, offset)

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        key_locators_occ = get_context().child[CN_INTERNAL].child[CN_KEY_LOCATORS]
        result = self.check_interference_cb.b_notify_execute_preview([o for o in key_locators_occ.child.values() if isinstance(o, F3Occurrence)])
        if result is None:
            self.execute_common(event_args)
        else:
            _, _, _, hit_kpns, _ = result
            if len(hit_kpns) == 0:
                self.execute_common(event_args)

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)


def check_interference(move_occs: ty.List[F3Occurrence], other_occs: ty.List[F3Occurrence] = []):
    # Interference check: CAUTION! It assumes all holes are included by MEVs about misc / foot parts!
    con = get_context()
    inl_occ = con.child[CN_INTERNAL]
    col_mev = CreateObjectCollectionT(af.BRepBody)
    col_hole = CreateObjectCollectionT(af.BRepBody)
    col_mf = CreateObjectCollectionT(af.BRepBody)

    col_misc = {AN_MEV: col_mev, AN_HOLE: col_mf, AN_MF: col_hole}
    move_refs: ty.List[ty.Tuple[af.BRepBody, int, str]] = []
    body_finder = BodyFinder()
    for i, mo in enumerate(move_occs):
        for an in [AN_MEV, AN_HOLE, AN_MF]:
            for b in body_finder.get(mo, an):
                tb = b.copyToComponent(con.comp)
                tb.isLightBulbOn = False
                col_misc[an].add(tb)
                move_refs.append((tb, i, an))

    col_kp_other = {AN_MEV: col_mev, AN_HOLE: col_hole, AN_MF: col_mf}
    fixed_refs: ty.List[ty.Tuple[af.BRepBody, VirtualF3Occurrence, str]] = []

    def _append_if_possible(fixed_body: af.BRepBody, parent_occ: VirtualF3Occurrence, category: str):
        if category == AN_MEV:
            target_category = AN_MEV
        elif category == AN_MF:
            target_category = AN_HOLE
        elif category == AN_HOLE:
            target_category = AN_MF
        else:
            raise BadCodeException()
        
        for tb, _, an in move_refs:
            if an == target_category and tb.boundingBox.intersects(fixed_body.boundingBox):
                col_kp_other[category].add(fixed_body)
                fixed_refs.append((fixed_body, parent_occ, category))
                return

    for kp_occ in inl_occ.child[CN_KEY_PLACEHOLDERS].child.values():
        for n, ka_occ in kp_occ.child.items():
            if n.endswith(CNP_KEY_ASSEMBLY):
                for po in ka_occ.child.values():
                    for an in ANS_HOLE_MEV_MF:
                        for b in body_finder.get(po, an):
                            tb = b.copyToComponent(con.comp)
                            tb.isLightBulbOn = False
                            _append_if_possible(tb, po, an)
    for o in other_occs:
        for an in ANS_HOLE_MEV_MF:
            for b in body_finder.get(o, an):
                tb = b.copyToComponent(con.comp)
                tb.isLightBulbOn = False
                _append_if_possible(tb, o, an)
    category_appearance = get_category_appearance()
    hits = [False, ] * len(move_occs)

    def _resolve(ent: ac.Base):
        temp_body = af.BRepBody.cast(ent)
        for b, i, an in move_refs:
            if b == temp_body:
                return i, an
        for b, o, an in fixed_refs:
            if b == temp_body:
                return o, an
        raise BadCodeException()

    def _show(ent: ac.Base, io: ty.Union[int, VirtualF3Occurrence], an: str):
        b = af.BRepBody.cast(ent)
        b.isLightBulbOn = True
        b.appearance = category_appearance[an]
        if isinstance(io, int):
            hits[io] = True
        else:
            io.light_bulb = False

    hit_bug = False
    for c in [col_mev, col_hole, col_mf]:
        if c.count < 2:
            continue
        inf_results = con.des.analyzeInterference(con.des.createInterferenceInput(c))
        if inf_results is None:
            hit_bug = True
            continue
        for ir in inf_results:
            io1, an1 = _resolve(ir.entityOne)
            io2, an2 = _resolve(ir.entityTwo)
            if isinstance(io1, int) or isinstance(io2, int):
                _show(ir.entityOne, io1, an1)
                _show(ir.entityTwo, io2, an2)
    if hit_bug:
        con.ui.messageBox('You came across a bug of Fusion 360. The interference check overlooks something.\nAbout the bug:\nhttps://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251')

    return hits


class PlaceMainboardCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.move_comp_cb: MoveComponentCommandBlock
        self.offset_cb: OffsetCommandBlock
        self.last_light_bulb = False

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
        self.last_boss = False
        con = get_context()
        hit_frame = False
        for b in list(con.comp.bRepBodies):
            if b.name == BN_FRAME:
                hit_frame = True
            if b.name.startswith(BN_MAINBOARD_BOSS):
                self.last_boss = True
                b.deleteMe()
        if not hit_frame:
            self.run_execute = False
            raise BadConditionException('Please generate a frame first.')

        self.move_comp_cb = MoveComponentCommandBlock(self)
        self.move_comp_cb.notify_create(event_args)

        self.offset_cb = OffsetCommandBlock(self)
        self.offset_cb.b_notify_create('Offset', '2 mm')

        layout_in = self.inputs.addRadioButtonGroupCommandInput(INP_ID_MAINBOARD_LAYOUT_RADIO, 'Layout')
        layout_in.listItems.add('Back', True)
        layout_in.listItems.add('Bottom', False)

        flip_in = self.inputs.addBoolValueInput(INP_ID_FLIP_BOOL, 'Flip', True)
        flip_in.value = False

        if_in = self.inputs.addBoolValueInput(INP_ID_CHECK_INTERFERENCE_BOOL, 'Check Interference', True)
        if_in.value = False

        inl_occ = con.child[CN_INTERNAL]
        inl_occ.light_bulb = True
        mp_occ = inl_occ.child.get_real(CN_MISC_PLACEHOLDERS)
        self.last_light_bulb = mp_occ.light_bulb
        mp_occ.light_bulb = True
        cn_mainboard = get_cn_mainboard()
        if cn_mainboard in mp_occ.child:
            o = mp_occ.child[cn_mainboard]
            if AN_MB_LOCATION_INPUTS in o.comp_attr:
                locs = pickle.loads(base64.b64decode(o.comp_attr[AN_MB_LOCATION_INPUTS]))
                for ci, v in zip(self.move_comp_cb.get_inputs(), locs[0]):
                    ci.value = v
                self.offset_cb.get_in().value = f'{locs[1] * 10} mm'
                for li in list(layout_in.listItems):
                    if li.name == locs[2]:
                        li.isSelected = True
                        break
                flip_in.value = locs[3]
            self.move_comp_cb.start_transaction(self.get_mainboard_transform())
        else:
            t = self.get_mainboard_transform()
            self.move_comp_cb.start_transaction(t)
            mb_occ = inl_occ.child[CN_DEPOT_PARTS].child[cn_mainboard]
            o = mp_occ.child.add(mb_occ, t)
            o.light_bulb = False
        body_finder = BodyFinder()
        for b in body_finder.get(o, AN_FILL):
            b.isLightBulbOn = True

    def get_layout_in(self):
        return get_ci(self.inputs, INP_ID_MAINBOARD_LAYOUT_RADIO, ac.RadioButtonGroupCommandInput)

    def get_flip_in(self):
        return get_ci(self.inputs, INP_ID_FLIP_BOOL, ac.BoolValueCommandInput)

    def get_check_interference_in(self):
        return get_ci(self.inputs, INP_ID_CHECK_INTERFERENCE_BOOL, ac.BoolValueCommandInput)

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
            elif changed_input.id == INP_ID_OFFSET_STR:
                t = self.get_mainboard_transform()
                self.move_comp_cb.start_transaction(t)
            self.move_comp_cb.b_notify_changed_input(changed_input)

    def execute_common(self, event_args: CommandEventArgs):
        con = get_context()
        o = con.child[CN_INTERNAL].child[CN_MISC_PLACEHOLDERS].child.get_real(get_cn_mainboard())
        o.transform = self.get_mainboard_transform()
        o.light_bulb = True
        self.move_comp_cb.b_notify_execute_preview(event_args, [o])
        return o

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        o = self.execute_common(event_args)

        if self.get_check_interference_in().value:
            other_occs: ty.List[F3Occurrence] = []
            inl_occ = get_context().child[CN_INTERNAL]
            if CN_FOOT_PLACEHOLDERS in inl_occ.child:
                other_occs.extend([o.child.get_real(CN_FOOT) for o in inl_occ.child[CN_FOOT_PLACEHOLDERS].child.values() if isinstance(o, F3Occurrence)])

            hits = check_interference([o], other_occs)
            o.light_bulb = not hits[0]

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        o = self.execute_common(event_args)
        o.comp_attr[AN_MB_LOCATION_INPUTS] = base64.b64encode(pickle.dumps([
            [ci.value for ci in self.move_comp_cb.get_inputs()],
            self.offset_cb.get_value(),
            self.get_layout_in().selectedItem.name,
            self.get_flip_in().value,
        ])).decode()
        self.last_boss = True

    def notify_destroy(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        mp_occ = con.child[CN_INTERNAL].child[CN_MISC_PLACEHOLDERS]
        if self.last_boss:
            o = mp_occ.child[get_cn_mainboard()]
            body_finder = BodyFinder()
            for b in body_finder.get(o, AN_FILL):
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
        self.last_foot_transforms: ty.Dict[str, ac.Matrix3D]
        self.last_light_bulb = False

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
        self.last_num_foot = 0
        self.last_foot_transforms = {}
        con = get_context()

        hit_frame = False
        for b in list(con.comp.bRepBodies):
            if b.name == BN_FRAME:
                hit_frame = True
            if b.name.startswith(BN_FOOT_BOSS):
                b.deleteMe()
        if not hit_frame:
            self.run_execute = False
            raise BadConditionException('Please generate a frame first.')

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

        for pn, po in fp_occ.child.items():
            if po.light_bulb:
                self.last_num_foot += 1
                self.last_foot_transforms[pn] = po.transform
        if self.last_num_foot != 4 and self.last_num_foot != 6 and self.last_num_foot != 8:
            self.last_num_foot = 0
            self.last_foot_transforms.clear()

        inputs = self.inputs

        nf_in = inputs.addRadioButtonGroupCommandInput(INP_ID_NUM_FOOT_RADIO, 'Num of feet')
        nf_in.listItems.add('4', self.last_num_foot == 4 or self.last_num_foot == 0)
        nf_in.listItems.add('6', self.last_num_foot == 6)
        nf_in.listItems.add('8', self.last_num_foot == 8)

        locator_in = inputs.addSelectionInput(INP_ID_FOOT_LOCATOR_SEL, 'Foot', 'Select an entity')
        locator_in.addSelectionFilter('SolidBodies')
        locator_in.setSelectionLimits(0, 0)

        self.move_comp_cb = MoveComponentCommandBlock(self)
        self.move_comp_cb.notify_create(event_args)
        self.offset_cb = OffsetCommandBlock(self)
        self.offset_cb.b_notify_create('Offset', fp_occ.comp_attr[AN_FOOT_OFFSET] if AN_FOOT_OFFSET in fp_occ.comp_attr else '0 mm')

        if_in = inputs.addBoolValueInput(INP_ID_CHECK_INTERFERENCE_BOOL, 'Check Interference', True)
        if_in.value = False

    def set_foot_transform(self, offset: float, num_foot: int):
        con = get_context()
        fb = get_frame().boundingBox
        inl_occ = con.child[CN_INTERNAL]
        fp_occ = inl_occ.child.get_real(CN_FOOT_PLACEHOLDERS)

        if len(self.last_foot_transforms) == num_foot:
            for foot_name, t in self.last_foot_transforms.items():
                fo = fp_occ.child[foot_name]
                nt = t.copy()
                nt.setCell(2, 3, fb.minPoint.z + offset - MIN_FLOOR_HEIGHT)
                fo.transform = nt
                fo.light_bulb = True
        else:
            locs: ty.List[ty.Tuple[float, float]]
            if num_foot == 4:
                locs = [(fb.minPoint.x, fb.maxPoint.y), (fb.maxPoint.x, fb.maxPoint.y), (fb.minPoint.x, fb.minPoint.y), (fb.maxPoint.x, fb.minPoint.y), ]
            elif num_foot == 6:
                locs = [(fb.minPoint.x, fb.maxPoint.y), (0., fb.maxPoint.y), (fb.maxPoint.x, fb.maxPoint.y),
                        (fb.minPoint.x, fb.minPoint.y), (0., fb.minPoint.y), (fb.maxPoint.x, fb.minPoint.y), ]
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
                t.setCell(2, 3, fb.minPoint.z + offset - MIN_FLOOR_HEIGHT)
                if rot:
                    t.setCell(0, 0, -1.)
                    t.setCell(1, 1, -1.)
                fo.transform = t
                fo.light_bulb = True

    def notify_pre_select(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        if active_input.id == INP_ID_FOOT_LOCATOR_SEL:
            e = af.BRepBody.cast(selection.entity)
            if e is None:
                event_args.isSelectable = False
                return
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

    def get_check_interference_in(self):
        return get_ci(self.inputs, INP_ID_CHECK_INTERFERENCE_BOOL, ac.BoolValueCommandInput)

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
        if changed_input.id == INP_ID_FOOT_LOCATOR_SEL:
            if has_sel_in(self.get_locator_in()):
                self.set_manipulator()
            else:
                self.move_comp_cb.stop_transaction()
        elif changed_input.id == INP_ID_NUM_FOOT_RADIO:
            if self.offset_cb.is_valid():
                self.get_locator_in().clearSelection()
                self.move_comp_cb.stop_transaction()
        self.move_comp_cb.b_notify_changed_input(changed_input)

    def execute_common(self, event_args: CommandEventArgs):
        locator_in = self.get_locator_in()
        selected_locators = [F3Occurrence(af.BRepBody.cast(locator_in.selection(i).entity).assemblyContext) for i in range(locator_in.selectionCount)]
        self.set_foot_transform(self.offset_cb.get_value(), self.get_num_foot())
        self.move_comp_cb.b_notify_execute_preview(event_args, selected_locators)

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
        if self.get_check_interference_in().value:
            inl_occ = get_context().child[CN_INTERNAL]
            other_occs: ty.List[F3Occurrence] = []
            if CN_MISC_PLACEHOLDERS in inl_occ.child:
                other_occs.extend([o for o in inl_occ.child[CN_MISC_PLACEHOLDERS].child.values() if isinstance(o, F3Occurrence)])
            fp_occ = inl_occ.child[CN_FOOT_PLACEHOLDERS]
            fos = [fp_occ.child[fn].child.get_real(CN_FOOT) for fn in FOOT_NAMES[:self.get_num_foot()]]
            hits = check_interference(fos, other_occs)
            for o, h in zip(fp_occ.child.values(), hits):
                if h:
                    o.child[CN_FOOT].light_bulb = False
                    for b in o.comp.bRepBodies:
                        b.opacity = 0.

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
        self.last_num_foot = self.get_num_foot()
        fp_occ = get_context().child[CN_INTERNAL].child[CN_FOOT_PLACEHOLDERS]
        fp_occ.comp_attr[AN_FOOT_OFFSET] = self.offset_cb.get_in().value
    
    def notify_destroy(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        inl_occ = con.child[CN_INTERNAL]
        fp_occ = inl_occ.child[CN_FOOT_PLACEHOLDERS]
        if self.last_num_foot != 0:
            fos = [fp_occ.child[fn].child.get_real(CN_FOOT) for fn in FOOT_NAMES[:self.get_num_foot()]]
            body_finder = BodyFinder()
            for o in fos:
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
        for b in body_finder.get(o, AN_HOLE):
            tb = b.copyToComponent(con.comp)
            hole_body_col.add(tb)

    before_frame_bodies = [b for b in con.comp.bRepBodies if b.isSolid]
    frame.name = BN_FRAME
    combines = con.root_comp.features.combineFeatures

    if len(hole_body_col) > 0:
        co_in4 = combines.createInput(frame, hole_body_col)
        co_in4.operation = af.FeatureOperations.CutFeatureOperation
        co_in4.isKeepToolBodies = False
        _ = combines.add(co_in4)

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
        if b.volume < CHIPPING_BODY_THRESHOLD:
            nbs.remove(b)

    inl_occ.light_bulb = False


class HolePartsCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()

    @property
    def cmd_name(self) -> str:
        return 'Hole'

    @property
    def tooltip(self) -> str:
        return 'Holes all parts, including the mainboard and feet. You can print the frame body after this command.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/hole'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        frame_in = self.inputs.addSelectionInput(INP_ID_FRAME_BODY_SEL, 'Frame Body', 'Select an entity')
        frame_in.addSelectionFilter('SolidBodies')
        frame_in.setSelectionLimits(1, 1)

    def get_frame_in(self):
        return get_ci(self.inputs, INP_ID_FRAME_BODY_SEL, ac.SelectionCommandInput)

    def execute_common(self, event_args: CommandEventArgs):
        frame = af.BRepBody.cast(self.get_frame_in().selection(0).entity)
        hole_all_parts(frame)

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
        event_args.isValidResult = True

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
