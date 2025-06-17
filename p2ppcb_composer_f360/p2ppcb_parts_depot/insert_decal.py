from dataclasses import dataclass
from collections.abc import Iterable
import pathlib

import adsk.core as ac
import adsk.fusion as af


ORIGIN_P = ac.Point3D.create(0, 0, 0)
EYE_POINT = ac.Point3D.create(0, 0, 70)


@dataclass
class InsertDecalParameter:
    '''
    Attributes and constructor's args
    ----------
    source_occurrence:
        The subject of Copy -> Paste-New operation.
    accommodate_occurrence:
        The destination place of Paste-New operation.
    new_name:
        The Paste-New-generated component's name.
    decal_image_file:
        PNG file.

    About the parameters below, leave them None when you leave as default.

    attributes:
        F360's component attributes set to the Paste-New-generated component.
    opacity:
        Same with the DECAL dialog. 0-100.
    [xy]_distance:
        centimeter
    z_angle:
        radian
    scale_[xy], scale_plane_xy, chain_faces:
        Same with the DECAL dialog.
    pointer_offset_[xyz]:
        Backward compatibility feature.
        In some cases, DECAL dialog result can be unstable if just the origin point was clicked.
        Offsetting from the origin point can cure it. The unit is centimeter.
    '''
    source_occurrence: af.Occurrence
    accommodate_occurrence: af.Occurrence
    new_name: str
    decal_image_file: pathlib.Path
    attributes: Iterable[tuple[str, str, str]] | None = None
    opacity: int | None = None
    x_distance: float | None = None
    y_distance: float | None = None
    z_angle: float | None = None
    scale_x: float | None = None
    scale_y: float | None = None
    scale_plane_xy: float | None = None
    chain_faces: bool | None = None
    pointer_offset_x: float | None = None
    pointer_offset_y: float | None = None
    pointer_offset_z: float | None = None


def start_batch(insert_decal_parameters: Iterable[InsertDecalParameter]):  # noqa: E501
    '''Runs a batch of InsertDecalParameter list.

    Parameters
    ----------
    insert_decal_parameters:
        You can process multiple source / decal image / dialog parameter set in a call.
    '''
    global APP
    APP = ac.Application.get()

    last_dt = APP.activeProduct.designType  # type: ignore
    APP.activeProduct.designType = af.DesignTypes.ParametricDesignType  # type: ignore  # Now (2025-06-15) Decal API cannot work in DirectDesignType.

    for i, p in enumerate(insert_decal_parameters):
        if insert_decal(p, ORIGIN_P):
            raise Exception(f'f360_insert_decal_rpa error: #{i} of insert_decal_parameters looks wrong.')

    APP.activeProduct.designType = last_dt  # type: ignore


def insert_decal(p: InsertDecalParameter, target_point: ac.Point3D) -> bool:
    if paste_new(p):
        return True

    po_x = 0. if p.pointer_offset_x is None else p.pointer_offset_x
    po_y = 0. if p.pointer_offset_y is None else p.pointer_offset_y
    po_z = 0. if p.pointer_offset_z is None else p.pointer_offset_z
    v_po = ac.Vector3D.create(po_x, po_y, po_z)
    tp = target_point.copy()
    tp.translateBy(v_po)

    rc: af.Component = APP.activeProduct.rootComponent  # type: ignore

    # find face to insert decal
    hit_points: ac.ObjectCollectionT[ac.Point3D] = ac.ObjectCollection.create()  # type: ignore
    faces: ac.ObjectCollectionT[af.BRepFace] = rc.findBRepUsingRay(  # type: ignore
        EYE_POINT,
        EYE_POINT.vectorTo(tp),
        af.BRepEntityTypes.BRepFaceEntityType,
        -1,
        True,
        hit_points
    )
    if len(faces) == 0:
        return True
    f = faces[0]
    tp = hit_points[0]
    decal_center_v = tp.asVector()

    # build transform Matrix3D
    mt = ac.Matrix3D.create()
    mt.setToIdentity()
    if p.scale_x is not None:
        mt.setCell(0, 0, p.scale_x)
    if p.scale_y is not None:
        mt.setCell(1, 1, p.scale_y)
    if p.scale_plane_xy is not None:
        x = mt.getCell(0, 0) * p.scale_plane_xy
        y = mt.getCell(1, 1) * p.scale_plane_xy
        mt.setCell(0, 0, x)
        mt.setCell(1, 1, y)

    # call API
    base_feature = rc.features.baseFeatures.add()
    if not base_feature.startEdit():
        raise Exception('BaseFeatures.startEdit() failed.')
    di = rc.decals.createInput(str(p.decal_image_file), [f], tp)
    dit = di.transform.copy()
    dit.invert()
    ta = dit.asArray()

    d_x = 0. if p.x_distance is None else p.x_distance
    d_y = 0. if p.y_distance is None else p.y_distance
    if d_x != 0. or d_y != 0.:
        xv = ac.Vector3D.create(*ta[0:3])
        xv.normalize()
        xv.scaleBy(d_x)
        yv = ac.Vector3D.create(*ta[4:7])
        yv.normalize()
        yv.scaleBy(d_y)
        dv = xv.copy()
        dv.add(yv)
        tp.translateBy(dv)
        hit_points.clear()
        faces: ac.ObjectCollectionT[af.BRepFace] = rc.findBRepUsingRay(  # type: ignore
            EYE_POINT,
            EYE_POINT.vectorTo(tp),
            af.BRepEntityTypes.BRepFaceEntityType,
            -1,
            True,
            hit_points
        )
        for ff, hp in zip(faces, hit_points):
            if f == ff:
                decal_center_v = hp.asVector()
                break

    mr = ac.Matrix3D.create()
    mr.setToIdentity()
    if p.z_angle is not None:
        zv = ac.Vector3D.create(*ta[8:11])
        zv.normalize()
        mr.setToRotation(p.z_angle, zv, ORIGIN_P)

    mt.transformBy(di.transform)
    mt.transformBy(mr)
    mt.translation = decal_center_v
    di.transform = mt
    di.targetBaseFeature = base_feature
    if p.chain_faces is not None:
        di.isChainFaces = p.chain_faces
    if p.opacity is not None:
        di.opacity = p.opacity / 100
    if not base_feature.finishEdit():
        raise Exception('BaseFeatures.finishEdit() failed.')
    _ = rc.decals.add(di)

    return False


def paste_new(p: InsertDecalParameter) -> bool:
    rc: af.Component = APP.activeProduct.rootComponent  # type: ignore

    def choose_light_bulb(os: Iterable[af.Occurrence]):
        acos = [rc.allOccurrencesByComponent(o.component)[0] for o in os]
        for aco in acos:
            ic = rc
            for n in aco.fullPathName.split('+'):
                for io in ic.occurrences:
                    io.isLightBulbOn = False
                io = ic.occurrences.itemByName(n)
                if io is None:
                    raise Exception('Occurrence.fullPathName seems wrong. Fusion 360 API broken?')
                ic = io.component
        for aco in acos:
            ic = rc
            for n in aco.fullPathName.split('+'):
                io = ic.occurrences.itemByName(n)
                if io is None:
                    raise Exception('Occurrence.fullPathName seems wrong. Fusion 360 API broken?')
                io.isLightBulbOn = True
                ic = io.component

    choose_light_bulb([p.source_occurrence, p.accommodate_occurrence])
    m = ac.Matrix3D.create()
    m.setToIdentity()
    o = p.accommodate_occurrence.component.occurrences.addNewComponentCopy(p.source_occurrence.component, m)
    if o is None:
        return True
    o.component.name = p.new_name

    if p.attributes is not None:
        for a in p.attributes:
            o.component.attributes.add(*a)

    o = o.createForAssemblyContext(p.accommodate_occurrence)
    choose_light_bulb([o])
    return False
