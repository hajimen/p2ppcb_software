from enum import IntEnum
import typing as ty
import pickle
from dataclasses import dataclass
import p2ppcb_parts_resolver.resolver as parts_resolver
from p2ppcb_parts_resolver.resolver import Part
import adsk
import adsk.core as ac
import adsk.fusion as af
from f360_common import AN_HOLE, AN_KEY_PLACEHOLDERS_SPECIFIER_OPTIONS_OFFSET, AN_KEY_V_OFFSET, AN_LOCATORS_I, \
    AN_LOCATORS_LEGEND_PICKLED, AN_LOCATORS_PATTERN_NAME, AN_LOCATORS_SPECIFIER, AN_MEV, AN_MF, ANS_OPTION, \
    ATTR_GROUP, CN_DEPOT_CAP_PLACEHOLDER, CN_DEPOT_KEY_ASSEMBLY, CN_DEPOT_PARTS, \
    CN_KEY_PLACEHOLDERS, EYE_M3D, F3D_DIRNAME, PN_USE_STABILIZER, CreateObjectCollectionT, \
    F3Occurrence, SpecsOpsOnPn, SurrogateF3Occurrence, VirtualF3Occurrence, cap_name, \
    cap_placeholder_name, capture_position, \
    get_context, CN_INTERNAL, CN_KEY_LOCATORS, ORIGIN_P3D, XU_V3D, \
    FourOrientation, TwoOrientation, YU_V3D, ZU_V3D, key_assembly_name, \
    key_placeholder_name, pcb_name, stabilizer_name, switch_name, ANS_HOLE_MEV_MF, get_parts_data_path
import p2ppcb_parts_depot.depot as parts_depot
from p2ppcb_composer.cmd_common import AN_LOCATORS_PLANE_TOKEN, AN_SKELETON_SURFACE, check_layout_plane

INP_ID_LAYOUT_PLANE_SEL = 'layoutPlane'
INP_ID_KEY_LOCATOR_SEL = 'keyLocator'

AN_LOCATORS_ANGLE_TOKEN = 'angleSurfaceToken'

# PP: Prepare Parameter
PP_KEY_ASSEMBLY_ON_SO = 'PP Key Assembly on Specifier name and Options'
PP_KEY_LOCATORS_ON_SPECIFIER = 'PP Key Locators on Specifier'
PP_SURROGATE_KEY_ASSEMBLY_NAMES = 'PP Surrogate Key Assembly Names'


class I_ANS_OPTION(IntEnum):
    CAP_DESC = 0
    STABILIZER_DESC = 1
    STABILIZER_ORIENTATION = 2
    SWITCH_DESC = 3
    SWITCH_ORIENTATION = 4
    KEY_V_ALIGN = 5


@dataclass
class PrepareKeyPlaceholderParameter:
    i: int
    legend: ty.List[str]


@dataclass
class PrepareKeyAssemblyParameter:
    pattern_name: str
    specifier: str
    cap_desc: str
    stabilizer_desc: str
    stabilizer_orientation: TwoOrientation
    switch_desc: str
    switch_orientation: FourOrientation
    align_to: parts_resolver.AlignTo
    offset: float
    kps: ty.List[PrepareKeyPlaceholderParameter]


def _find_hit_point_face(hit_points, hit_faces, surface: af.BRepBody):
    '''
    hit_points: ac.ObjectCollectionT[ac.Point3D]
    hit_faces: ac.ObjectCollectionT[af.BRepFace]
    '''
    for p, f in zip(hit_points, hit_faces):
        if f.body == surface:
            return p, f
    return None, None


def _get_proxy_transform(raw_occ: ty.Optional[af.Occurrence]):
    if raw_occ is None:  # af.Occurrence.cast(entity) is None when entity is a root component.
        return EYE_M3D.copy()

    occ = F3Occurrence(raw_occ)
    o = occ
    ret = EYE_M3D.copy()
    while True:
        ret.transformBy(o.transform)
        if occ.has_parent:
            o = occ.parent
        else:
            break
    return ret


def place_key_placeholders(kl_occs: ty.Optional[ty.List[VirtualF3Occurrence]] = None):
    con = get_context()

    pp_ka_on_so: ty.Dict[str, PrepareKeyAssemblyParameter] = con.prepare_parameter_dict[PP_KEY_ASSEMBLY_ON_SO]
    pp_ka_on_so.clear()
    skeleton_surface = af.BRepBody.cast(con.attr_singleton[AN_SKELETON_SURFACE][1])
    ss_comp = skeleton_surface.parentComponent
    ss_trans = _get_proxy_transform(skeleton_surface.assemblyContext)
    ss_inv_trans = ss_trans.copy()
    ss_inv_trans.invert()

    inl_occ = con.child[CN_INTERNAL]
    locators_occ = inl_occ.child[CN_KEY_LOCATORS]
    key_placeholders_occ = inl_occ.child.get_real(CN_KEY_PLACEHOLDERS)

    if kl_occs is None:
        kl_occs = list(locators_occ.child.values())

    for kl_occ in kl_occs:
        pattern_name = kl_occ.comp_attr[AN_LOCATORS_PATTERN_NAME]
        specifier = kl_occ.comp_attr[AN_LOCATORS_SPECIFIER]
        i = int(kl_occ.comp_attr[AN_LOCATORS_I])
        options = [kl_occ.comp_attr[an] for an in ANS_OPTION]
        offset_str = kl_occ.comp_attr[AN_KEY_V_OFFSET]
        specifier_options_offset_joined = specifier + ' ' + ' '.join(options) + ' ' + offset_str
        specifier_options = ' '.join([specifier, ] + options)
        legend_pickled = kl_occ.comp_attr[AN_LOCATORS_LEGEND_PICKLED]
        legend: ty.List[str] = pickle.loads(bytes.fromhex(legend_pickled))

        def _on_surrogate_kp(o: VirtualF3Occurrence):
            o.comp_attr[AN_KEY_PLACEHOLDERS_SPECIFIER_OPTIONS_OFFSET] = specifier_options_offset_joined
            if specifier_options in pp_ka_on_so:
                pp = pp_ka_on_so[specifier_options]
                for kp in pp.kps:
                    if kp.i == i and kp.legend == legend:
                        return
            else:
                pp = PrepareKeyAssemblyParameter(
                    pattern_name,
                    specifier,
                    options[I_ANS_OPTION.CAP_DESC],
                    options[I_ANS_OPTION.STABILIZER_DESC],
                    TwoOrientation[options[I_ANS_OPTION.STABILIZER_ORIENTATION]],
                    options[I_ANS_OPTION.SWITCH_DESC],
                    FourOrientation[options[I_ANS_OPTION.SWITCH_ORIENTATION]],
                    parts_resolver.AlignTo[options[I_ANS_OPTION.KEY_V_ALIGN]],
                    float(offset_str),
                    []
                )
                pp_ka_on_so[specifier_options] = pp
            pp.kps.append(PrepareKeyPlaceholderParameter(i, legend))

        kn = key_placeholder_name(i, pattern_name)
        if kn in key_placeholders_occ.child:
            kp_occ = key_placeholders_occ.child[kn]
            if kp_occ.comp_attr[AN_KEY_PLACEHOLDERS_SPECIFIER_OPTIONS_OFFSET] != specifier_options_offset_joined:
                del key_placeholders_occ.child[kn]
                kp_occ = key_placeholders_occ.child.get(kn, on_surrogate=_on_surrogate_kp)
        else:
            kp_occ = key_placeholders_occ.child.get(kn, on_surrogate=_on_surrogate_kp)
        kp_occ.light_bulb = False

        zv = ac.Vector3D.create(0., 0., -1.)
        root_kl_trans = kl_occ.transform.copy()
        root_kl_trans.transformBy(locators_occ.transform)
        zv.transformBy(root_kl_trans)
        zv_ss = zv.copy()
        zv_ss.transformBy(ss_inv_trans)
        orig = ORIGIN_P3D.copy()
        orig.transformBy(root_kl_trans)
        orig_ss = orig.copy()
        orig_ss.transformBy(ss_inv_trans)
        hit_points = CreateObjectCollectionT(ac.Point3D)
        hit_faces: ac.ObjectCollectionT[af.BRepFace]
        hit_faces = ss_comp.findBRepUsingRay(orig_ss, zv_ss, af.BRepEntityTypes.BRepFaceEntityType, -1., False, hit_points)  # type: ignore
        center, _ = _find_hit_point_face(hit_points, hit_faces, skeleton_surface)
        if center is None:
            continue
        center.transformBy(ss_trans)

        ka_surface = af.BRepBody.cast(con.find_by_token(kl_occ.comp_attr[AN_LOCATORS_ANGLE_TOKEN])[0])
        ka_comp = ka_surface.parentComponent
        ka_trans = _get_proxy_transform(ka_surface.assemblyContext)
        ka_inv_trans = ka_trans.copy()
        ka_inv_trans.invert()
        zv_ka = zv.copy()
        zv_ka.transformBy(ka_inv_trans)
        orig_ka = orig.copy()
        orig_ka.transformBy(ka_inv_trans)
        hit_points.clear()
        hit_faces = ka_comp.findBRepUsingRay(orig_ka, zv_ka, af.BRepEntityTypes.BRepFaceEntityType, -1., False, hit_points)  # type: ignore
        ka_point, ka_face = _find_hit_point_face(hit_points, hit_faces, ka_surface)
        if ka_point is None or ka_face is None:
            continue
        success, ka_normal = ka_face.evaluator.getNormalAtPoint(ka_point)
        if not success:
            continue
        ka_normal.transformBy(ka_trans)
        ka_normal.normalize()

        rot = ac.Matrix3D.create()
        rot.setToRotateTo(ZU_V3D, ka_normal)

        lp = af.ConstructionPlane.cast(con.find_by_token(kl_occ.comp_attr[AN_LOCATORS_PLANE_TOKEN])[0])
        lp_inv_trans = get_layout_plane_transform(lp)
        if lp_inv_trans is None:
            raise Exception('Bad code.')
        lp_inv_trans.invert()

        t = root_kl_trans.copy()
        t.transformBy(lp_inv_trans)
        _, xv, yv, _ = t.getAsCoordinateSystem()
        xv.transformBy(rot)
        yv.transformBy(rot)
        kp_trans = ac.Matrix3D.create()
        kp_trans.setWithCoordinateSystem(center, xv, yv, ka_normal)

        kp_occ.transform = kp_trans
        kp_occ.light_bulb = True


_BACK_TRANS = ac.Matrix3D.create()
_BACK_TRANS.setWithArray(
    (-1., 0., 0., 0.,
     0., -1., 0., 0.,
     0., 0., 1., 0.,
     0., 0., 0., 1.))


_RIGHT_TRANS = ac.Matrix3D.create()
_RIGHT_TRANS.setWithArray(
    (0., -1., 0., 0.,
     1., 0., 0., 0.,
     0., 0., 1., 0.,
     0., 0., 0., 1.))


_LEFT_TRANS = ac.Matrix3D.create()
_LEFT_TRANS.setWithArray(
    (0., 1., 0., 0.,
     -1., 0., 0., 0.,
     0., 0., 1., 0.,
     0., 0., 0., 1.))


def prepare_key_assembly(
        specs_ops_on_pn: SpecsOpsOnPn,
        pi: parts_resolver.PartsInfo) -> ty.List[parts_depot.PreparePartParameter]:

    con = get_context()
    inl_occ = con.child[CN_INTERNAL]

    depot_key_assembly_occ = inl_occ.child.get_real(CN_DEPOT_KEY_ASSEMBLY)
    depot_key_assembly_occ.light_bulb = False

    depot_parts_occ = inl_occ.child.get_real(CN_DEPOT_PARTS)
    depot_parts_occ.light_bulb = False

    key_placeholders_occ = inl_occ.child.get_real(CN_KEY_PLACEHOLDERS)
    key_placeholders_occ.light_bulb = True

    depot_cap_placeholder_occ = inl_occ.child.get_real(CN_DEPOT_CAP_PLACEHOLDER)
    depot_cap_placeholder_occ.light_bulb = False

    pp_ka_on_so: ty.Dict[str, 'PrepareKeyAssemblyParameter'] = con.prepare_parameter_dict[PP_KEY_ASSEMBLY_ON_SO]
    pps_part: ty.List[parts_depot.PreparePartParameter] = []
    pp_surrogate_ka_names: ty.Dict[str, ty.Any] = con.prepare_parameter_dict[PP_SURROGATE_KEY_ASSEMBLY_NAMES]

    def _create_part_trans(z_pos: float):
        t = EYE_M3D.copy()
        t.setCell(2, 3, z_pos)
        return t

    for _, pka in pp_ka_on_so.items():
        pattern_name = pka.pattern_name
        specifier = pka.specifier
        cap_desc = pka.cap_desc
        stabilizer_desc = pka.stabilizer_desc
        stabilizer_orientation = pka.stabilizer_orientation
        switch_desc = pka.switch_desc
        switch_orientation = pka.switch_orientation
        desc_on_part = {Part.Cap: cap_desc, Part.Stabilizer: stabilizer_desc, Part.Switch: switch_desc, Part.PCB: switch_desc}  # 'Part.PCB: switch_desc' is intentional.
        align_to = pka.align_to
        offset = pka.offset
        specs_ops = specs_ops_on_pn[pattern_name]

        part_filename, part_parameters, part_placeholder, part_z_pos, switch_xya = pi.resolve_specifier(specifier, cap_desc, stabilizer_desc, switch_desc, align_to)

        if PN_USE_STABILIZER in part_parameters[Part.Stabilizer]:
            if part_parameters[Part.Stabilizer][PN_USE_STABILIZER].m_as('mm') == 0:
                del part_z_pos[Part.Stabilizer]
            del part_parameters[Part.Stabilizer][PN_USE_STABILIZER]
        else:
            del part_z_pos[Part.Stabilizer]

        part_trans = {
            p: _create_part_trans(part_z_pos[p].m_as('cm'))
            for p in parts_resolver.PARTS_WITH_COMPONENT
            if p in part_z_pos
        }

        t = EYE_M3D.copy()
        switch_angle = switch_xya[parts_resolver.SPN_SWITCH_ANGLE].m_as('rad')
        if switch_angle != 0.:
            t.setToRotation(switch_angle, ZU_V3D, ORIGIN_P3D)
        t.setCell(0, 3, switch_xya[parts_resolver.SPN_SWITCH_X].m_as('cm'))
        t.setCell(1, 3, switch_xya[parts_resolver.SPN_SWITCH_Y].m_as('cm'))
        for p in [Part.Stabilizer, Part.Switch, Part.PCB]:
            if p in part_trans:
                part_trans[p].transformBy(t)

        offset_trans = ac.Matrix3D.create()
        offset_trans.setCell(2, 3, offset)

        parts_data_path = get_parts_data_path()

        def _on_surrogate_parts(p: Part):
            if p == Part.Cap:
                def _on_surrogate_cap(occ: SurrogateF3Occurrence):
                    new_pp_cap = parts_depot.PreparePartParameter(
                        str(parts_data_path / F3D_DIRNAME / part_filename[Part.Cap]),
                        occ.name,
                        part_parameters[Part.Cap],
                        part_placeholder.get(Part.Cap, 'Placeholder')
                    )
                    pp_cap = None
                    for p in pps_part:
                        same = True
                        for pn in ['part_source_filename', 'new_name', 'model_parameters', 'placeholder']:
                            same = same and (getattr(p, pn) == getattr(new_pp_cap, pn))
                        if same:
                            pp_cap = p
                            break
                    if pp_cap is None:
                        new_pp_cap.cap_placeholder_parameters = parts_depot.CapPlaceholderParameter(
                            pi.resolve_decal(specifier, cap_desc),
                            []
                        )
                        pp_cap = new_pp_cap
                        pps_part.append(pp_cap)
                    if pp_cap.cap_placeholder_parameters is None:
                        raise Exception('Bad code.')
                    pp_cap.cap_placeholder_parameters.names_images.extend([
                        (
                            cap_placeholder_name(kp.i, cap_desc, specifier, kp.legend),
                            None if specs_ops[kp.i][1] is None else specs_ops[kp.i][1].image_file_path  # type: ignore
                        )
                        for kp in pka.kps
                    ])
                return _on_surrogate_cap
            else:
                def _on_surrogate_part(occ: SurrogateF3Occurrence):
                    new_pp_part = parts_depot.PreparePartParameter(
                        str(parts_data_path / F3D_DIRNAME / part_filename[p]),
                        occ.name,
                        part_parameters[p]
                    )
                    if new_pp_part not in pps_part:
                        pps_part.append(new_pp_part)
                return _on_surrogate_part

        def _on_surrogate_rigid(occ: SurrogateF3Occurrence):
            occ.rigid_in_replace = True

        def _on_surrogate_ka(ka_occ: SurrogateF3Occurrence):
            pp_surrogate_ka_names[ka_occ.name] = None
            for p, pn, orientation in zip(
                    [Part.Cap, Part.Stabilizer, Part.Switch, Part.PCB],
                    [cap_name, stabilizer_name, switch_name, pcb_name],
                    [TwoOrientation.Front, stabilizer_orientation, switch_orientation, switch_orientation]):
                if p in part_trans:
                    part_occ = depot_parts_occ.child.get(
                        pn(desc_on_part[p], specifier),
                        on_surrogate=_on_surrogate_parts(p))
                    pt = part_trans[p].copy()
                    if orientation is TwoOrientation.Back:
                        pt.transformBy(_BACK_TRANS)
                    elif orientation is FourOrientation.Back:
                        pt.transformBy(_BACK_TRANS)
                    elif orientation is FourOrientation.Left:
                        pt.transformBy(_LEFT_TRANS)
                    elif orientation is FourOrientation.Right:
                        pt.transformBy(_RIGHT_TRANS)
                    o = ka_occ.child.add(part_occ, pt, on_surrogate=_on_surrogate_rigid)
                    o.light_bulb = True

        ka_occ = depot_key_assembly_occ.child.get(
            key_assembly_name(specifier, cap_desc, stabilizer_desc, stabilizer_orientation.name, switch_desc, switch_orientation.name, align_to.name),
            on_surrogate=_on_surrogate_ka)
        for kp in pka.kps:
            def _on_create_kp(kp_occ: F3Occurrence):
                cpn = cap_placeholder_name(kp.i, cap_desc, specifier, kp.legend)
                if cpn in depot_cap_placeholder_occ.child:
                    cp_occ = depot_cap_placeholder_occ.child[cpn]
                else:
                    cp_occ = depot_cap_placeholder_occ.child.new_surrogate(cpn)
                pt = part_trans[Part.Cap].copy()
                pt.transformBy(offset_trans)
                o = kp_occ.child.add(cp_occ, pt)
                o.light_bulb = True
                o = kp_occ.child.add(ka_occ, offset_trans)
                o.light_bulb = True

            kpn = key_placeholder_name(kp.i, pattern_name)
            surrogate_kp_occ = key_placeholders_occ.child[kpn]
            if not isinstance(surrogate_kp_occ, SurrogateF3Occurrence):
                raise Exception(f'Bad code. Key Placeholder name: {kpn} should be a surrogate.')
            surrogate_kp_occ.replace(on_create=_on_create_kp)

    pp_ka_on_so.clear()
    return pps_part


def _check_intra_key_assembly_interference(ka_occ_list: ty.List[VirtualF3Occurrence]) -> ty.List[str]:
    con = get_context()
    AN_ORIGINAL_BODY_NAME = 'originalBodyName'

    def _get_original_body_name(b: af.BRepBody):
        bn = b.attributes.itemByName(ATTR_GROUP, AN_ORIGINAL_BODY_NAME)
        if bn is None:
            raise Exception('Bad code.')
        return bn.value

    error_messages: ty.List[str] = []
    for ka_occ in ka_occ_list:
        hit_bug = False
        col_mev = CreateObjectCollectionT(af.BRepBody)
        temp_refs: ty.List[ty.Tuple[af.BRepBody, str]] = []
        col_hole_mf = CreateObjectCollectionT(af.BRepBody)
        result_str_list = []
        for pn, po in ka_occ.child.items():
            for an in ANS_HOLE_MEV_MF:
                for b in po.bodies_by_attr(an):
                    tb = b.copyToComponent(con.comp)
                    temp_refs.append((tb, pn))
                    tb.attributes.add(ATTR_GROUP, AN_ORIGINAL_BODY_NAME, b.name)
                    if an == AN_MEV:
                        col_mev.add(tb)
                    elif an == AN_HOLE:
                        col_hole_mf.add(tb)
                    elif an == AN_MF:
                        col_hole_mf.add(tb)

        if len(col_mev) > 1:
            inf_in = con.des.createInterferenceInput(col_mev)
            inf_results = con.des.analyzeInterference(inf_in)
            if inf_results is None:
                hit_bug = True
            else:
                for ir in inf_results:
                    pns: ty.List[str] = []
                    bns: ty.List[str] = []
                    for e in [ir.entityOne, ir.entityTwo]:
                        b = af.BRepBody.cast(e)  # native object, not proxy
                        bns.append(_get_original_body_name(b))
                        for rb, pn in temp_refs:
                            if rb == b:
                                pns.append(pn)
                                break
                    result_str_list.append(f'MEV to MEV:\n  parts: {pns[0]} <--> {pns[1]}\n  bodies: {bns[0]} <--> {bns[1]}')

        if len(col_hole_mf) > 1:
            inf_in = con.des.createInterferenceInput(col_hole_mf)
            inf_results = con.des.analyzeInterference(inf_in)
            if inf_results is None:
                hit_bug = True
            else:
                for ir in inf_results:
                    bs: ty.List[af.BRepBody] = []
                    ans: ty.List[str] = []
                    for e in [ir.entityOne, ir.entityTwo]:
                        b = af.BRepBody.cast(e)
                        bs.append(b)
                        ans.append(b.attributes[0].name)
                    if all(an == AN_HOLE for an in ans) or all(an == AN_MF for an in ans):
                        continue

                    pn_hole = ''
                    bn_hole = ''
                    pn_mf = ''
                    bn_mf = ''
                    for b, an in zip(bs, ans):
                        for rb, pn in temp_refs:
                            if rb == b:
                                if an == AN_HOLE:
                                    pn_hole = pn
                                    bn_hole = _get_original_body_name(b)
                                else:
                                    pn_mf = pn
                                    bn_mf = _get_original_body_name(b)
                    result_str_list.append(f'Hole to MF:\n  parts: {pn_hole} <--> {pn_mf}\n  bodies: {bn_hole} <--> {bn_mf}')

        for tb, _ in temp_refs:
            tb.deleteMe()
        if len(result_str_list) > 0:
            msg = f'Key Assembly {ka_occ.name} has interference between its parts. You should avoid the combination of the parts.\n\n' + '\n'.join(result_str_list)
            error_messages.append(msg)
        if hit_bug:
            msg = f'You came across a bug of Fusion 360 while checking Key Assembly {ka_occ.name}. The interference check overlooks something.\nAbout the bug:\nhttps://forums.autodesk.com/t5/fusion-360-support/obvious-interference-was-not-detected/m-p/10633251'
            error_messages.append(msg)

    return error_messages


def fill_surrogate():
    con = get_context()
    inl_occ = con.child[CN_INTERNAL]
    key_placeholders_occ = inl_occ.child[CN_KEY_PLACEHOLDERS]
    kd = {n: o.transform for n, o in key_placeholders_occ.child.items()}

    depot_key_assembly_occ = inl_occ.child.get_real(CN_DEPOT_KEY_ASSEMBLY)
    depot_key_assembly_occ.light_bulb = True  # F360's bug workaround: https://forums.autodesk.com/t5/fusion-360-api-and-scripts/api-bug-occurrence-islightbulbon-did-not-work-properly/td-p/9531468
    for o in list(depot_key_assembly_occ.child.values()):
        if isinstance(o, SurrogateF3Occurrence):
            o.replace()
    depot_key_assembly_occ.light_bulb = False

    for _, o in key_placeholders_occ.child.items():
        last_bulb = o.light_bulb  # F360's bug workaround
        o.light_bulb = True
        for oo in list(o.child.values()):
            if isinstance(oo, SurrogateF3Occurrence):
                oo.replace()
        o.light_bulb = last_bulb

    for n, o in key_placeholders_occ.child.items():
        o.transform = kd[n]
    capture_position()

    pp_surrogate_ka_names: ty.Dict[str, ty.Any] = con.prepare_parameter_dict[PP_SURROGATE_KEY_ASSEMBLY_NAMES]
    ka_occ_list = [depot_key_assembly_occ.child[kan] for kan in pp_surrogate_ka_names]
    error_messages = _check_intra_key_assembly_interference(ka_occ_list)
    for msg in error_messages:
        con.ui.messageBox(msg)
    pp_surrogate_ka_names.clear()


def prepare_parts_sync(pps_part: ty.List[parts_depot.PreparePartParameter], cache_docname: ty.Optional[str] = None):
    con = get_context()
    pd = parts_depot.PartsDepot(cache_docname)
    pp_kl_on_specifier: ty.Dict[str, parts_depot.PrepareKeyLocatorParameter] = con.prepare_parameter_dict[PP_KEY_LOCATORS_ON_SPECIFIER]
    pls = list(pp_kl_on_specifier.values())
    prepare_finished = False
    prepare_success = False

    def _error():
        nonlocal prepare_finished
        try:
            pd.close()
        finally:
            prepare_finished = True

    def _next():
        nonlocal prepare_finished, prepare_success
        try:
            pd.close()
            pp_kl_on_specifier.clear()
            pps_part.clear()
            prepare_success = True
        finally:
            prepare_finished = True

    pd.prepare(con.child.get_real(CN_INTERNAL), pls, pps_part, _next, _error)

    while not prepare_finished:
        adsk.doEvents()

    if prepare_success:
        capture_position()
        fill_surrogate()
    return prepare_success


def get_layout_plane_transform(cp: af.ConstructionPlane):
    cp_plane = check_layout_plane(cp)

    z_axis_i_line = ac.InfiniteLine3D.create(ORIGIN_P3D, ZU_V3D)
    z_point = cp_plane.intersectWithLine(z_axis_i_line)
    xy = ac.Plane.createUsingDirections(ORIGIN_P3D, XU_V3D, YU_V3D)
    if cp_plane.isParallelToPlane(xy):
        cp_xy = XU_V3D.copy()
    else:
        cp_xy_line = cp_plane.intersectWithPlane(xy)
        cp_xy = cp_xy_line.direction.copy()
        cp_xy.normalize()
        if cp_xy.x < 0:
            cp_xy.scaleBy(-1.0)
    cp_y = cp_plane.normal.crossProduct(cp_xy)

    t = ac.Matrix3D.create()
    t.setWithCoordinateSystem(z_point, cp_xy, cp_y, cp_plane.normal)
    return t
