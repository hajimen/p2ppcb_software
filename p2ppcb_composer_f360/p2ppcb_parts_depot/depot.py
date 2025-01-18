import re
import sys
import pathlib
import hashlib
import json
import traceback
import time
import typing as ty
from dataclasses import dataclass
from pint import Quantity
import numpy as np
from PIL import Image
import adsk.core as ac
import adsk.fusion as af
import adsk


from f360_insert_decal_rpa import start as insert_decal_rpa_start
from f360_insert_decal_rpa import InsertDecalParameter
from f360_common import ANS_KEY_PITCH, BN_APPEARANCE_KEY_LOCATOR, CN_DEPOT_APPEARANCE, CN_DEPOT_PARTS, CN_KEY_LOCATORS, CURRENT_DIR, BadCodeException, BadConditionException, F3AttributeDict, F3Occurrence, CNP_KEY_LOCATOR, CN_DEPOT_CAP_PLACEHOLDER, ATTR_GROUP, \
    CreateObjectCollectionT, SurrogateF3Occurrence, catch_exception, create_component, MAGIC, CNP_CAP_PLACEHOLDER, get_context, prepare_tmp_dir, reset_context, set_context

CUSTOM_EVENT_DONE_ID = 'rpa_done'
CUSTOM_EVENT_ERROR_ID = 'rpa_error'

DEFAULT_CACHE_DOCNAME = 'P2PPCB Cache'

CN_SRC_FIXED = 'Source Fixed'
CNP_FIXED = '_F'
CN_SRC_DECALED = 'Source Decaled'
CNP_DECALED = '_D'
CN_SRC_KEY_LOCATOR = 'Source Key Locator'
CNP_LOCATOR_IMG = '_KLI'
CN_SRC_CAP_PLACEHOLDER = 'Source Cap Placeholder'
CNP_CP_IMG_CPDP = '_CPII'
CN_CONTAINER = 'P2PPCB Container'
CN_DEPOT_PORTING = 'Port from Cache' + MAGIC
PCN_DEPOT_PORTING = 'DP_'  # PCN: prefix component name
CNP_DEPOT_PORTING = '_DP' + MAGIC

HANDLERS: ty.Dict[str, ac.CustomEventHandler] = {}


@dataclass
class CapPlaceholderParameter:
    decal_parameters: ty.Dict[str, Quantity]
    names_images: ty.List[ty.Tuple[str, ty.Optional[pathlib.Path]]]


@dataclass
class PrepareKeyLocatorParameter:
    decal_parameters: ty.Dict[str, Quantity]
    pattern: np.ndarray
    pitch_wd: ty.Dict[str, Quantity]
    names_images: ty.List[ty.Tuple[str, ty.Optional[pathlib.Path]]]


@dataclass
class PreparePartParameter:
    part_source_filename: str
    new_name: ty.Optional[str]
    model_parameters: ty.Dict[str, Quantity]
    placeholder: ty.Union[str, None] = None
    cap_placeholder_parameters: ty.Union[CapPlaceholderParameter, None] = None


def open_a360_file(folder: ac.DataFolder, name: str) -> ac.DataFile:
    for _ in range(5):
        for ii in range(folder.dataFiles.count):
            try:
                f = folder.dataFiles[ii]
                adsk.doEvents()
            except Exception:
                time.sleep(.4)
                continue
            if f.name == name:
                return f
        time.sleep(.4)
        adsk.doEvents()
    raise FileNotFoundError(f'Cannot find {name}.')


def convert_quantity_to_float(qs: ty.Dict[str, Quantity]):
    ret: ty.Dict[str, float] = {}
    for k, v in qs.items():
        if v.is_compatible_with('rad'):
            ret[k] = v.m_as('rad')  # dimensionless value too
        elif v.is_compatible_with('cm'):
            ret[k] = v.m_as('cm')
        else:
            raise BadCodeException(f'Unknown dimension in part info: {str(v)}')
    return ret


class EventAndHandler:
    def __init__(self, handler: ac.CustomEventHandler, event_id: str) -> None:
        con = get_context()
        con.app.unregisterCustomEvent(event_id)
        self.event = con.app.registerCustomEvent(event_id)
        self.event.add(handler)
        self.event_id = event_id
        HANDLERS[event_id] = handler

    def finish(self) -> None:
        con = get_context()
        if self.event is None:
            return
        self.event.remove(HANDLERS[self.event_id])
        con.app.unregisterCustomEvent(self.event_id)
        self.event = None
        del HANDLERS[self.event_id]


class RpaEventHandler(ac.CustomEventHandler):
    def __init__(self, parts_depot: 'PartsDepot', call: ty.Callable) -> None:
        super().__init__()
        self.parts_depot = parts_depot
        self.call = call

    @catch_exception
    def notify(self, _) -> None:
        self.parts_depot.finish_rpa()
        self.call()


def create_key_locator_surface_by_pattern(pattern: np.ndarray, pitch_wd: ty.Dict[str, Quantity], occ: F3Occurrence) -> None:
    lp = np.zeros((pattern.shape[0] + 2, pattern.shape[1] + 2), np.bool_)
    lp[1:-1, 1:-1] = pattern
    cw = np.array([[0, -1], [1, 0]], int)
    ccw = np.array([[0, 1], [-1, 0]], int)
    initial_yx = np.argwhere(lp)[0]
    yx = initial_yx
    current_direction = np.array([0, 1], int)
    vertices_list = []
    directions_list: ty.List[np.ndarray] = []
    while True:
        go_on = len(directions_list) > 0
        hit = False
        for _ in range(4):
            left_pixel_yx = yx + np.where((current_direction @ ccw) + current_direction == 1, 0, -1)  # type: ignore
            right_pixel_yx = yx + np.where((current_direction @ cw) + current_direction == 1, 0, -1)  # type: ignore
            if (not lp[tuple(left_pixel_yx)]) and lp[tuple(right_pixel_yx)]:
                if go_on:
                    directions_list[-1] = directions_list[-1] + current_direction
                else:
                    vertices_list.append(yx)
                    directions_list.append(current_direction)  # type: ignore
                yx = yx + current_direction
                hit = True
                break
            go_on = False
            current_direction = current_direction @ cw
        if not hit:
            raise BadCodeException('Cannot find edge in key pattern.')
        if np.all(yx == initial_yx):
            break
    vertices = (np.array(vertices_list) - np.array(lp.shape) / 2) / 4
    directions = np.array(directions_list) / 4
    sketch: af.Sketch = occ.comp.sketches.add(occ.comp.xYConstructionPlane)
    lines = sketch.sketchCurves.sketchLines
    p: float = min([pitch_wd[an].m_as('cm') for an in ANS_KEY_PITCH])
    # src_slc = CreateObjectCollectionT(af.SketchLine)
    src_slc: list[af.SketchCurve] = []
    for v, d in zip(vertices, directions):
        s = v * p
        s = (s[1], -s[0])
        e = (v + d) * p
        e = (e[1], -e[0])
        sl = lines.addByTwoPoints(
            ac.Point3D.create(*s, 0.),
            ac.Point3D.create(*e, 0.)
        )
        src_slc.append(sl)
    # new_slc: ac.ObjectCollectionT[af.SketchLine] = sketch.offset(
    #     src_slc, ac.Point3D.create(0., 0., 0.),
    #     (p * (54 - 42)) / 2 / 54  # KLE's pitch is 54 and key top is 42.
    # )  # type: ignore
    ci = sketch.geometricConstraints.createOffsetInput(
        src_slc,
        ac.ValueInput.createByReal((p * (54 - 42)) / 2 / 54)  # KLE's pitch is 54 and key top is 42.
    )
    oc = sketch.geometricConstraints.addOffset2(ci)
    new_slc = [af.SketchLine.cast(c) for c in oc.childCurves]

    for sl in src_slc:
        sl.deleteMe()

    arcs = sketch.sketchCurves.sketchArcs
    for i in range(len(new_slc)):
        sl1 = new_slc[i]
        sl2 = new_slc[(i + 1) % len(new_slc)]
        sl1.length
        arcs.addFillet(sl1, sl1.endSketchPoint.geometry, sl2, sl2.startSketchPoint.geometry, 0.2)
    prof = sketch.profiles[0]
    pa_in = occ.comp.features.patchFeatures.createInput(prof, af.FeatureOperations.NewBodyFeatureOperation)
    pa_f = occ.comp.features.patchFeatures.add(pa_in)
    con = get_context()
    ab = con.child[CN_DEPOT_APPEARANCE].comp.bRepBodies.itemByName(BN_APPEARANCE_KEY_LOCATOR)
    if ab is None:
        raise BadCodeException(f'appearance.f3d is corrupted. It lacks {BN_APPEARANCE_KEY_LOCATOR} body.')
    kl_appearance = ab.appearance
    for b in pa_f.bodies:
        b.appearance = kl_appearance


class PartsDepot:
    def __init__(self, cache_docname=None) -> None:
        self.is_close = False
        self.cache_docname = DEFAULT_CACHE_DOCNAME if cache_docname is None else cache_docname
        con = get_context()
        orig_doc = con.app.activeDocument
        admin_folder: ac.DataFolder = con.app.data.dataProjects[0].rootFolder
        try:
            _ = open_a360_file(admin_folder, self.cache_docname)
        except FileNotFoundError:
            doc: ac.Document = con.app.documents.add(ac.DocumentTypes.FusionDesignDocumentType)
            newdoc_con = get_context(af.Design.cast(doc.products[0]))

            im = newdoc_con.app.importManager
            with create_component(newdoc_con.comp, CN_DEPOT_APPEARANCE):
                im.importToTarget(im.createFusionArchiveImportOptions(str(CURRENT_DIR / 'f3d' / 'appearance.f3d')), newdoc_con.comp)
            newdoc_con.child[CN_DEPOT_APPEARANCE].light_bulb = False

            newdoc_con.des.designType = af.DesignTypes.DirectDesignType
            _ = newdoc_con.child.new_real(CN_SRC_FIXED)
            decaled_root_occ = newdoc_con.child.new_real(CN_SRC_DECALED)
            _ = decaled_root_occ.child.new_real(CN_SRC_CAP_PLACEHOLDER)
            _ = decaled_root_occ.child.new_real(CN_SRC_KEY_LOCATOR)

            doc.saveAs(self.cache_docname, admin_folder, 'P2PPCB Cache', '')
            doc.close(False)
        cache_doc = None
        for _ in range(10):
            try:
                cf = open_a360_file(admin_folder, self.cache_docname)
                cache_doc = con.app.documents.open(cf, True)
            except RuntimeError:
                # simply retry
                for _ in range(10):
                    time.sleep(.2)
                    adsk.doEvents()
                continue
            break
        if cache_doc is None:
            raise BadConditionException(f'Cannot open {self.cache_docname}. Internet connection or Autodesk A360 service may be too slow.')
        self.cache_doc = cache_doc
        self.cache_doc_is_modified = False
        orig_doc.activate()

        self.pattern_hashes: ty.Optional[ty.List[str]] = None
        self.fp_hashes: ty.Optional[ty.List[str]] = None

        # f360_insert_decal_rpa
        self.done: ty.Union[EventAndHandler, None] = None
        self.error: ty.Union[EventAndHandler, None] = None

    def _prepare_context(self):
        if self.is_close:
            raise BadConditionException('Already closed.')
        con = get_context()
        self.orig_con = con
        self.orig_doc = con.app.activeDocument
        if not self.orig_doc.isSaved:
            raise BadConditionException('Start from a saved document.')
        try:
            self.cache_doc.activate()
        except RuntimeError:
            pass  # I don't know why "RuntimeError: 2 : InternalValidationError : res" occurs. F360's bug? But activate() works nevertheless.
        return reset_context(af.Design.cast(self.cache_doc.products[0]))

    def prepare(self, acc_occ: F3Occurrence, prepare_locator_parameters: ty.List[PrepareKeyLocatorParameter], prepare_part_parameters: ty.List[PreparePartParameter], next: ty.Callable, error: ty.Callable, silent=False) -> None:
        def on_create_cache_doc_modified(_):
            self.cache_doc_is_modified = True

        con = self._prepare_context()
        fixed_root_occ = con.child.get_real(CN_SRC_FIXED, on_create=on_create_cache_doc_modified)
        decaled_root_occ = con.child.get_real(CN_SRC_DECALED, on_create=on_create_cache_doc_modified)
        locator_root_occ = decaled_root_occ.child.get_real(CN_SRC_KEY_LOCATOR, on_create=on_create_cache_doc_modified)

        pattern_hashes: ty.List[str] = []
        locator_decal_redundant_check: ty.Dict[str, ty.Set[str]] = {}
        idps: ty.List[InsertDecalParameter] = []
        locator_hashes_on_patterns: ty.List[ty.List[str]] = []

        for lp in prepare_locator_parameters:
            locator_hashes: ty.List[str] = []

            def on_create_locator_pattern_occ(occ: F3Occurrence):
                self.cache_doc_is_modified = True
                create_key_locator_surface_by_pattern(lp.pattern, lp.pitch_wd, occ)

            pattern_hash_bytes = str(lp.pitch_wd).encode() + lp.pattern.tobytes()
            pattern_hash = hashlib.md5(pattern_hash_bytes).hexdigest()
            if pattern_hash not in locator_decal_redundant_check:
                locator_decal_redundant_check[pattern_hash] = set()
            pattern_hashes.append(pattern_hash)
            locator_src_occ = decaled_root_occ.child.get_real(pattern_hash + CNP_DECALED, on_create=on_create_locator_pattern_occ)
            locator_acc_occ = locator_root_occ.child.get_real(pattern_hash + CNP_KEY_LOCATOR, on_create=on_create_cache_doc_modified)

            for _, image in lp.names_images:
                if image is None:
                    img_hash_bytes = b''
                else:
                    pil_image = Image.open(image)
                    all_white = True
                    for rgb in pil_image.getdata():
                        if rgb != (255, 255, 255):
                            all_white = False
                            break
                    if all_white:
                        image = None
                        img_hash_bytes = b''
                    else:
                        img_hash_bytes = Image.open(image).tobytes()
                # img_hash_bytes = Image.open(image).tobytes()
                pattern_img_hash = hashlib.md5(pattern_hash_bytes + img_hash_bytes).hexdigest()
                locator_hashes.append(pattern_img_hash)
                comp_name = pattern_img_hash + CNP_LOCATOR_IMG
                if pattern_img_hash not in locator_decal_redundant_check[pattern_hash]:
                    locator_decal_redundant_check[pattern_hash].add(pattern_img_hash)
                    if image is None:
                        target_occ = locator_acc_occ.child.get_real(comp_name)
                        for b in locator_src_occ.comp.bRepBodies:
                            b.copyToComponent(target_occ.raw_occ)
                        target_occ.comp.attributes.add('P2PPCB Depot', 'pattern_hash', hashlib.md5(pattern_hash_bytes).hexdigest())
                        target_occ.comp.attributes.add('P2PPCB Depot', 'img_hash', hashlib.md5(img_hash_bytes).hexdigest())
                    elif comp_name not in locator_acc_occ.child:
                        idps.append(InsertDecalParameter(
                            locator_src_occ.raw_occ,
                            locator_acc_occ.raw_occ,
                            comp_name,
                            image,
                            attributes=[
                                ('P2PPCB Depot', 'pattern_hash', hashlib.md5(pattern_hash_bytes).hexdigest()),
                                ('P2PPCB Depot', 'img_hash', hashlib.md5(img_hash_bytes).hexdigest())
                            ],
                            **convert_quantity_to_float(lp.decal_parameters)))
            locator_hashes_on_patterns.append(locator_hashes)

        self.pattern_hashes = pattern_hashes
        self.locator_hashes_on_patterns = locator_hashes_on_patterns
        self.names_images_on_patterns = [lp.names_images for lp in prepare_locator_parameters]

        # fp: fixed part
        fp_comps: ty.List[af.Component] = []
        fp_hashes: ty.List[str] = []
        for pp in prepare_part_parameters:
            fp_hash_src = (pp.part_source_filename, pp.placeholder, pp.cap_placeholder_parameters is None, tuple((k, str(v)) for k, v in sorted(pp.model_parameters.items())))
            fp_hash = hashlib.md5(json.dumps(fp_hash_src).encode()).hexdigest()
            if fp_hash in fp_hashes:
                fp_comps.append(fp_comps[fp_hashes.index(fp_hash)])
                fp_hashes.append(fp_hash)
                continue
            fp_hashes.append(fp_hash)
            if fp_hash + CNP_FIXED not in fixed_root_occ.child:
                self.cache_doc_is_modified = True
                if con.des.designType == af.DesignTypes.DirectDesignType:
                    con.des.designType = af.DesignTypes.ParametricDesignType  # for model parameters
                with create_component(fixed_root_occ.comp, fp_hash, CNP_FIXED) as container:
                    im = con.app.importManager
                    try:
                        for _ in range(200):  # F360's bug workaround
                            time.sleep(0.01)
                            adsk.doEvents()
                        im.importToTarget(im.createFusionArchiveImportOptions(pp.part_source_filename), fixed_root_occ.comp)
                        for _ in range(200):  # F360's bug workaround
                            time.sleep(0.01)
                            adsk.doEvents()
                    except Exception:
                        raise BadConditionException(f'F3D file import failed: {pp.part_source_filename}')
                comp = container.pop().comp
                for k, v in pp.model_parameters.items():
                    for mp in comp.modelParameters:
                        if mp.name == k or mp.name.startswith(k + '_'):
                            if v.is_compatible_with('rad'):
                                mp.value = v.m_as('rad')
                            elif v.is_compatible_with('cm'):
                                mp.value = v.m_as('cm')
                            else:
                                raise BadCodeException(f'Unknown dimension in part info: {str(v)}')
                if pp.cap_placeholder_parameters is not None:
                    for b in comp.bRepBodies:
                        a = b.attributes.itemByName(ATTR_GROUP, 'Placeholder')
                        if a is not None:
                            b.isLightBulbOn = False
            else:
                comp = fixed_root_occ.child.get_real(fp_hash + CNP_FIXED).comp
            fp_comps.append(comp)

        if con.des.designType == af.DesignTypes.ParametricDesignType:
            con.des.designType = af.DesignTypes.DirectDesignType

        # Child components are no use as parts. They are just for dependency of parametric design.
        for comp in fp_comps:
            for o in list(comp.occurrences):
                o.deleteMe()

        # cp: cap placeholder
        cp_root_occ = decaled_root_occ.child[CN_SRC_CAP_PLACEHOLDER]
        cp_decal_redundant_check: ty.Set[str] = set()
        cp_img_cpdp_hashes_on_fps: ty.List[ty.Optional[ty.List[str]]] = []
        for pp, fp_comp, fp_hash in zip(prepare_part_parameters, fp_comps, fp_hashes):
            if pp.cap_placeholder_parameters is None:
                cp_img_cpdp_hashes_on_fps.append(None)
            else:
                cp_img_cpdp_hashes: ty.List[str] = []

                def on_create_cp_src_occ(new_occ: F3Occurrence):
                    self.cache_doc_is_modified = True
                    for b in fp_comp.bRepBodies:
                        ad = F3AttributeDict(b.attributes)
                        if 'Placeholder' in ad and ad['Placeholder'] == pp.placeholder:
                            b.copyToComponent(new_occ.raw_occ)
                    for b in new_occ.comp.bRepBodies:
                        b.isLightBulbOn = True

                cp_src_occ = decaled_root_occ.child.get_real(fp_hash + CNP_DECALED, on_create=on_create_cp_src_occ)
                cp_acc_occ = cp_root_occ.child.get_real(fp_hash + CNP_CAP_PLACEHOLDER, on_create=on_create_cache_doc_modified)

                cpdp_hash_bytes = json.dumps(tuple((k, str(v)) for k, v in sorted(pp.cap_placeholder_parameters.decal_parameters.items()))).encode()

                for _, image in pp.cap_placeholder_parameters.names_images:
                    if image is None:
                        img_hash_bytes = b''
                    else:
                        pil_image = Image.open(image)
                        all_white = True
                        for rgb in pil_image.getdata():  # type: ignore
                            if rgb != (255, 255, 255):
                                all_white = False
                                break
                        if all_white:
                            image = None
                            img_hash_bytes = b''
                        else:
                            img_hash_bytes = Image.open(image).tobytes()
                    cp_img_cpdp_hash = hashlib.md5(bytes.fromhex(fp_hash) + img_hash_bytes + cpdp_hash_bytes).hexdigest()
                    comp_name = cp_img_cpdp_hash + CNP_CP_IMG_CPDP
                    cp_img_cpdp_hashes.append(cp_img_cpdp_hash)
                    if cp_img_cpdp_hash not in cp_decal_redundant_check:
                        cp_decal_redundant_check.add(cp_img_cpdp_hash)
                        if image is None:
                            target_occ = cp_acc_occ.child.get_real(comp_name)
                            for b in cp_src_occ.comp.bRepBodies:
                                b.copyToComponent(target_occ.raw_occ)
                            target_occ.comp.attributes.add('P2PPCB Depot', 'fp_hash', fp_hash)
                            target_occ.comp.attributes.add('P2PPCB Depot', 'cpdp_hash', hashlib.md5(cpdp_hash_bytes).hexdigest())
                            target_occ.comp.attributes.add('P2PPCB Depot', 'img_hash', hashlib.md5(img_hash_bytes).hexdigest())
                        elif comp_name not in cp_acc_occ.child:
                            idps.append(InsertDecalParameter(
                                cp_src_occ.raw_occ, cp_acc_occ.raw_occ, comp_name, image,
                                attributes=[
                                    ('P2PPCB Depot', 'fp_hash', fp_hash),
                                    ('P2PPCB Depot', 'cpdp_hash', hashlib.md5(cpdp_hash_bytes).hexdigest()),
                                    ('P2PPCB Depot', 'img_hash', hashlib.md5(img_hash_bytes).hexdigest())
                                ], **convert_quantity_to_float(pp.cap_placeholder_parameters.decal_parameters)))
                cp_img_cpdp_hashes_on_fps.append(cp_img_cpdp_hashes)

        self.fp_hashes = fp_hashes
        self.cp_img_cpdp_hashes_on_fps = cp_img_cpdp_hashes_on_fps
        self.new_name_on_fps = [pp.new_name for pp in prepare_part_parameters]
        self.names_images_on_fps = [pp.cap_placeholder_parameters.names_images if pp.cap_placeholder_parameters is not None else None for pp in prepare_part_parameters]

        # prepare f360_insert_decal_rpa
        self.done = EventAndHandler(RpaEventHandler(self, lambda: self.prepare_next(acc_occ, next, error)), CUSTOM_EVENT_DONE_ID)
        self.error = EventAndHandler(RpaEventHandler(self, error), CUSTOM_EVENT_ERROR_ID)

        if len(idps) > 0:
            self.cache_doc_is_modified = True
            insert_decal_rpa_start(CUSTOM_EVENT_DONE_ID, CUSTOM_EVENT_ERROR_ID, ac.ViewOrientations.TopViewOrientation, ac.Point3D.create(0., 0., 0.), idps, silent)
        else:
            con.app.fireCustomEvent(CUSTOM_EVENT_DONE_ID)

    def _prepare_next_impl(self, acc_occ: F3Occurrence) -> None:
        con = get_context()

        def exec(cmd, fail_object):
            result = con.app.executeTextCommand(cmd)
            if result != 'Ok':
                raise BadCodeException(f"Failed to do {fail_object}.")
        
        def copy_paste_new(obj_occ: F3Occurrence, acc_occ: F3Occurrence, new_name: str, is_visible: bool):
            acs = con.ui.activeSelections
            if new_name is acc_occ.child:
                del acc_occ.child[new_name]
            with create_component(acc_occ.comp, new_name) as container:
                acs.clear()
                acs.add(obj_occ.raw_occ)
                exec('Commands.Start CopyCommand', 'Ctrl-C copy')
                acs.clear()
                acs.add(acc_occ.raw_occ)
                exec('Commands.Start FusionPasteNewCommand', '"Paste New"')
                exec('NuCommands.CommitCmd', 'OK in the dialog')
                acs.clear()
            o = container.pop()
            o.light_bulb = is_visible
            return

        if self.cache_doc_is_modified:
            old_ver = self.cache_doc.dataFile.versionNumber
            self.cache_doc.save('prepare_next() started.')
            self.cache_doc.close(False)
            for _ in range(10):
                adsk.doEvents()
                admin_folder: ac.DataFolder = con.app.data.dataProjects[0].rootFolder
                cf = open_a360_file(admin_folder, self.cache_docname)
                if cf.versionNumber > old_ver:
                    self.cache_doc = con.app.documents.open(cf, True)
                    break
            self.cache_doc_is_modified = False
            con = reset_context()

        fixed_root_occ = con.child[CN_SRC_FIXED]
        decaled_root_occ = con.child[CN_SRC_DECALED]
        container_occ = ty.cast(F3Occurrence, con.child.new_real(CN_CONTAINER))

        if self.fp_hashes is not None:
            cp_root_occ = decaled_root_occ.child[CN_SRC_CAP_PLACEHOLDER]
            cp_root_occ.light_bulb = True
            cp_acc_occ = container_occ.child.new_real(PCN_DEPOT_PORTING + CN_DEPOT_CAP_PLACEHOLDER + CNP_DEPOT_PORTING)
            cp_acc_occ.light_bulb = True
            fixed_acc_occ = container_occ.child.new_real(PCN_DEPOT_PORTING + CN_DEPOT_PARTS + CNP_DEPOT_PORTING)
            for fp_hash, cp_img_cpdp_hashes, new_name, names_images in zip(
                self.fp_hashes, self.cp_img_cpdp_hashes_on_fps, self.new_name_on_fps, self.names_images_on_fps
            ):
                if new_name is not None:
                    n = PCN_DEPOT_PORTING + new_name + CNP_DEPOT_PORTING
                    if n not in fixed_acc_occ.child:
                        copy_paste_new(
                            fixed_root_occ.child.get_real(fp_hash + CNP_FIXED),
                            fixed_acc_occ,
                            n,
                            False
                        )
                if cp_img_cpdp_hashes is not None and names_images is not None:
                    cp_pp_occ = cp_root_occ.child[fp_hash + CNP_CAP_PLACEHOLDER]
                    for cp_img_cpdp_hash, (name, _) in zip(cp_img_cpdp_hashes, names_images):
                        copy_paste_new(
                            cp_pp_occ.child.get_real(cp_img_cpdp_hash + CNP_CP_IMG_CPDP),
                            cp_acc_occ,
                            PCN_DEPOT_PORTING + name + CNP_DEPOT_PORTING,
                            False
                        )
            cp_acc_occ.light_bulb = False
            cp_root_occ.light_bulb = False
            fixed_acc_occ.light_bulb = False

        if self.pattern_hashes is not None and self.names_images_on_patterns is not None:
            locator_root_occ = decaled_root_occ.child[CN_SRC_KEY_LOCATOR]
            locator_root_occ.light_bulb = True
            locator_acc_occ = container_occ.child.new_real(PCN_DEPOT_PORTING + CN_KEY_LOCATORS + CNP_DEPOT_PORTING)
            locator_acc_occ.light_bulb = True
            for pattern_hash, locator_hashes, names_images in zip(self.pattern_hashes, self.locator_hashes_on_patterns, self.names_images_on_patterns):
                if pattern_hash is not None and locator_hashes is not None:
                    locator_pattern_occ = locator_root_occ.child[pattern_hash + CNP_KEY_LOCATOR]
                    for locator_hash, (name, _) in zip(locator_hashes, names_images):
                        copy_paste_new(
                            locator_pattern_occ.child.get_real(locator_hash + CNP_LOCATOR_IMG),
                            locator_acc_occ,
                            PCN_DEPOT_PORTING + name + CNP_DEPOT_PORTING,
                            False
                        )
            locator_acc_occ.light_bulb = False
            locator_root_occ.light_bulb = False

        fp = prepare_tmp_dir() / 'cache_container.f3d'
        if fp.is_file():
            fp.unlink()
        fn = str(fp)
        em = con.des.exportManager
        try:
            em.execute(em.createFusionArchiveExportOptions(fn, container_occ.comp))  # very time consuming. 30 sec or above.
        except Exception:
            print(f'F3D file export failed: {fn}', file=sys.stderr)
            raise

        container_occ.raw_occ.nativeObject.deleteMe()

        self.orig_doc.activate()

        con = set_context(self.orig_con)
        # i_timeline_before = con.des.timeline.count

        im = con.app.importManager
        im_opt = im.createFusionArchiveImportOptions(fn)
        dp_occ = acc_occ.child.get_real(CN_DEPOT_PORTING)
        dp_occ.light_bulb = False

        from datetime import datetime
        one_time_name = datetime.now().strftime(r"%Y/%m/%d %H:%M:%S")
        with create_component(dp_occ.comp, one_time_name) as c:
            try:
                im.importToTarget(im_opt, dp_occ.comp)  # very time consuming. 60 sec or above.
            except Exception:
                print(f'F3D file import failed: {fn}', file=sys.stderr)
                raise
        imported_occ = c.pop()

        dp_name_re = re.compile(f'{PCN_DEPOT_PORTING}(.*){CNP_DEPOT_PORTING}')  # F360's component name is unique including deleted component.

        def rec_move(src_occ: F3Occurrence, acc_occ: F3Occurrence):
            m = dp_name_re.match(src_occ.name)
            if m is None:
                raise BadCodeException()
            rn = m.groups()[0]
            if len(src_occ.child) > 0:
                if not all([n.startswith(PCN_DEPOT_PORTING) for n in src_occ.child]):
                    raise BadCodeException('All components should be start with PCN_DEPOT_PORTING.')
                tgt_occ = acc_occ.child.get_real(rn)
                for cn in list(src_occ.child):
                    rec_move(src_occ.child.get_real(cn), tgt_occ)
            else:
                if rn in acc_occ.child:
                    ao = acc_occ.child[rn]
                    if isinstance(ao, SurrogateF3Occurrence):
                        src_occ.name = rn
                        o = ao.replace(real_occ=src_occ)
                        o.light_bulb = True
                    return
                else:
                    o = src_occ.move_to(acc_occ, rn)
                    o.light_bulb = True

        for cn in list(imported_occ.child):
            o = imported_occ.child.get_real(cn)
            rec_move(o, acc_occ)
        
        # i_timeline_after = con.des.timeline.count
        # tg = con.des.timeline.timelineGroups.add(i_timeline_before, i_timeline_after - 1)
        # tg.name = 'P2PPCB Insert'

    def prepare_next(self, acc_occ: F3Occurrence, next: ty.Callable, error: ty.Callable) -> None:
        try:
            self._prepare_next_impl(acc_occ)
        except Exception as e:
            traceback.print_exc()
            get_context().ui.messageBox(str(e), 'P2PPCB')
            error()
            return
        next()

    def close(self) -> None:
        if self.is_close:
            return
        self.cache_doc.close(False)  # Save when updated
        self.is_close = True

    def finish_rpa(self) -> None:
        for x in [self.done, self.error]:
            if x is not None:
                x.finish()
