from enum import Enum, auto
import sys
import base64
import zlib
import hashlib
from collections import defaultdict
from dataclasses import dataclass
import pathlib
import traceback
import typing as ty
from contextlib import contextmanager
from pint import Quantity
import p2ppcb_parts_resolver.resolver as parts_resolver
import adsk.core as ac
import adsk.fusion as af
import adsk

MIN_FLOOR_HEIGHT = 0.2

EYE_M3D = ac.Matrix3D.create()
ORIGIN_P3D = ac.Point3D.create(0, 0, 0)
XU_V3D = ac.Vector3D.create(1, 0, 0)
YU_V3D = ac.Vector3D.create(0, 1, 0)
ZU_V3D = ac.Vector3D.create(0, 0, 1)
CURRENT_DIR = pathlib.Path(__file__).parent
PARTS_DATA_DIR = CURRENT_DIR.parent / 'p2ppcb_parts_data_f360'
F3D_DIRNAME = 'f3d'


ATTR_GROUP = 'P2PPCB'

# F360 cannot have two same component names. To avoid name collision to user, MAGIC is added after CN for P2PPCB.
MAGIC = ' mU0jU'

# PN: Parameter Name
PN_USE_STABILIZER = 'UseStabilizer'

# CN: Component Name
# CNP: Component Name Postfix
CN_INTERNAL = 'P2PPCB Internal'
CN_KEY_LOCATORS = 'Key Locators' + MAGIC
CN_KEY_PLACEHOLDERS = 'Key Placeholders' + MAGIC
CN_MISC_PLACEHOLDERS = 'Misc Placeholders' + MAGIC
CN_FOOT_PLACEHOLDERS = 'Foot Placeholders' + MAGIC
CN_DEPOT_KEY_ASSEMBLY = 'Depot Key Assembly' + MAGIC
CNP_KEY_LOCATOR = '_KL'
CNP_KEY_PLACEHOLDER = '_KP'
CNP_KEY_ASSEMBLY = '_KA'
CN_DEPOT_CAP_PLACEHOLDER = 'Depot Cap Placeholder' + MAGIC
CNP_CAP_PLACEHOLDER = '_CP'
CN_DEPOT_PARTS = 'Depot Parts' + MAGIC
CNP_PARTS = '_P'
CN_DEPOT_APPEARANCE = 'Depot Appearance' + MAGIC
CN_MAINBOARD_ALICE = 'Alice' + CNP_PARTS
CN_FOOT = 'Foot' + CNP_PARTS

# BN: Body Name
BN_APPEARANCE_KEY_LOCATOR = 'Key Locator'
BN_APPEARANCE_HOLE = 'Hole'
BN_APPEARANCE_MEV = 'MEV'
BN_APPEARANCE_MF = 'MF'

# AN: Attribute Name
AN_PARTS_DATA_PATH = 'partsDataPath'

AN_MEV = 'MEV'
AN_MF = 'MF'
AN_HOLE = 'Hole'
AN_FILL = 'Fill'
AN_TERRITORY = 'Territory'
ANS_HOLE_MEV_MF = [AN_HOLE, AN_MEV, AN_MF]
AN_PLACEHOLDER = 'Placeholder'

AN_LOCATORS_PATTERN_NAME = 'locatorsPatternName'
AN_LOCATORS_SPECIFIER = 'locatorsSpecifier'
AN_LOCATORS_I = 'locatorsI'
AN_LOCATORS_LEGEND_PICKLED = 'locatorsLegendPickled'
AN_KEY_PLACEHOLDERS_SPECIFIER_OPTIONS_OFFSET = 'keyPlaceholdersSpecifierDescs'

AN_CAP_DESC = 'capDesc'
AN_STABILIZER_DESC = 'stabilizerDesc'
AN_STABILIZER_ORIENTATION = 'stabilizerOrientation'
AN_SWITCH_DESC = 'switchDesc'
AN_SWITCH_ORIENTATION = 'switchOrientation'
AN_KEY_V_ALIGN = 'keyVAlign'
AN_KEY_V_OFFSET = 'keyVOffset'
ANS_OPTION = [AN_CAP_DESC, AN_STABILIZER_DESC, AN_STABILIZER_ORIENTATION, AN_SWITCH_DESC, AN_SWITCH_ORIENTATION, AN_KEY_V_ALIGN]

AN_KEY_PITCH = 'keyPitch'
AN_ROW_NAME = 'rowName'
AN_COL_NAME = 'colName'
ANS_RC_NAME = [AN_ROW_NAME, AN_COL_NAME]

AN_KLE_B64 = 'kleB64'


DECAL_DESC_KEY_LOCATOR = 'Key Locator'

VirtualF3Occurrence = ty.Union['SurrogateF3Occurrence', 'F3Occurrence']
VirtualComponent = ty.Union['SurrogateComponent', af.Component]
SpecsOpsOnPn = ty.Dict[str, ty.List[ty.Tuple[str, ty.Optional[parts_resolver.OccurrenceParameter]]]]


def _DO_NOTHING(*args, **kwargs):
    return


def capture_position():
    con = get_context()
    if con.des.designType == af.DesignTypes.ParametricDesignType and con.des.snapshots.hasPendingSnapshot:
        con.des.snapshots.add()


class TwoOrientation(Enum):
    Front = auto()
    Back = auto()


class FourOrientation(Enum):
    Front = auto()
    Back = auto()
    Left = auto()
    Right = auto()


class F3AttributeDict(ty.MutableMapping[str, str]):
    def __init__(self, raw_attrs: ac.Attributes) -> None:
        super().__init__()
        self.raw_attrs = raw_attrs

    def __getitem__(self, name: str):
        a = self.raw_attrs.itemByName(ATTR_GROUP, name)
        if a is None:
            raise KeyError(f'{name} not found.')
        return a.value

    def __setitem__(self, name: str, value: str):
        a = self.raw_attrs.itemByName(ATTR_GROUP, name)
        if a is not None:
            a.deleteMe()
        self.raw_attrs.add(ATTR_GROUP, name, value)

    def __delitem__(self, name: str):
        a = self.raw_attrs.itemByName(ATTR_GROUP, name)
        if a is None:
            raise KeyError(f'{name} not found.')
        a.deleteMe()

    def __iter__(self):
        for a in self.raw_attrs:
            yield a.name

    def __len__(self):
        return self.raw_attrs.count

    def __contains__(self, name: str):
        return self.raw_attrs.itemByName(ATTR_GROUP, name) is not None


class F3OccurrenceDict(ty.Mapping[str, VirtualF3Occurrence]):
    def __init__(self, parent: ty.Union[af.Component, VirtualF3Occurrence]) -> None:
        # super().__init__()  # It overwrites get() method.
        if isinstance(parent, af.Component):
            self.parent_comp = parent
            self.parent_occ = None
        else:
            pc = parent.comp
            if isinstance(pc, af.Component):
                self.parent_comp = pc
                self.parent_occ = parent
            else:  # SurrogateComponent
                self.parent_comp = None
                self.parent_occ = parent

        self.surrogate_occs: ty.Union[ty.List[SurrogateF3Occurrence], SurrogateOccurrences] = [] if isinstance(parent, af.Component) else SurrogateOccurrences(parent)

    def _proxy_if_required(self, o: af.Occurrence):
        if self.parent_occ is None:
            return o
        elif isinstance(self.parent_occ, SurrogateF3Occurrence):
            raise Exception("Bad code.")
        return o.createForAssemblyContext(self.parent_occ.raw_occ)

    def __getitem__(self, name: str) -> VirtualF3Occurrence:
        if self.parent_comp is not None:
            for o in self.parent_comp.occurrences:
                if o.component.name == name:
                    return F3Occurrence(self._proxy_if_required(o))
        for o in self.surrogate_occs:
            if o.name == name:
                return o
        raise KeyError(f'{name} not found.')

    def __delitem__(self, name: str):
        if isinstance(self[name], F3Occurrence):
            self[name].raw_occ.deleteMe()  # type: ignore
            return
        else:
            for o in list(self.surrogate_occs):
                if o.name == name:
                    self.surrogate_occs.remove(o)
                    return
        raise KeyError(f'{name} not found.')

    def __iter__(self):
        if self.parent_comp is not None:
            for o in self.parent_comp.occurrences:
                yield o.component.name
        for o in self.surrogate_occs:
            yield o.name

    def __len__(self):
        rc = self.parent_comp.occurrences.count if self.parent_comp is not None else 0
        return rc + len(self.surrogate_occs)

    def __contains__(self, name: str):
        if self.parent_comp is not None:
            for o in self.parent_comp.occurrences:
                if o.component.name == name:
                    return True
        for o in self.surrogate_occs:
            if o.name == name:
                return True
        return False

    def new_real(self, name: str, overwrite=False, transform: ac.Matrix3D = EYE_M3D):
        if self.parent_comp is None:
            raise Exception('The parent is a surrogate.')
        if name in self:
            if overwrite:
                del self[name]
            else:
                raise Exception(f'{name} already exists.')
        capture_position()
        o = self.parent_comp.occurrences.addNewComponent(transform)
        o = self._proxy_if_required(o)
        o.component.name = name
        if o.component.name != name:  # name collision
            raise KeyError(f'{name} raises name collision. All components should have identical name.')
        return F3Occurrence(o)

    def new_surrogate(self, name: str, overwrite=False, transform: ac.Matrix3D = EYE_M3D, comp: ty.Optional[VirtualComponent] = None):
        if self.parent_occ is None:
            raise Exception('Impossible case. Bad code somewhere.')
        if name in self:
            if overwrite:
                del self[name]
            else:
                raise Exception(f'{name} already exists.')
        o = SurrogateF3Occurrence(name, self.parent_occ, transform, comp)
        self.surrogate_occs.append(o)
        return o

    def new(self, name: str, overwrite=False, transform: ac.Matrix3D = EYE_M3D) -> VirtualF3Occurrence:
        if self.parent_comp is None:
            return self.new_surrogate(name, overwrite, transform)
        else:
            return self.new_real(name, overwrite=overwrite, transform=transform)

    def add(self, f3occ: VirtualF3Occurrence, transform: ac.Matrix3D = EYE_M3D, on_surrogate: ty.Callable = _DO_NOTHING) -> VirtualF3Occurrence:
        if isinstance(f3occ, F3Occurrence) and self.parent_comp is not None:
            capture_position()
            o = self.parent_comp.occurrences.addExistingComponent(f3occ.comp, EYE_M3D)
            o = self._proxy_if_required(o)
            for _ in range(5):
                o.transform = transform
            return F3Occurrence(o)
        else:
            if self.parent_occ is None:
                raise Exception('add() with SurrogateF3Occurrence is not available to root component.')
            o = self.parent_occ.child.new_surrogate(f3occ.name, transform=transform, comp=f3occ.comp)
            on_surrogate(o)
            return o

    def get_real(self, name: str, on_create: ty.Callable = _DO_NOTHING) -> 'F3Occurrence':
        '''
        Creates new occurrence when it doesn't have a child of the name. Always real, never surrogate.
        on_create: Call when created.
        '''
        if self.parent_comp is None:
            raise Exception('The parent occ is a surrogate.')
        if name in self:
            o = self[name]
            if not isinstance(o, F3Occurrence):
                raise Exception('There is a surrogate of the name.')
        else:
            o = self.new_real(name)
            if on_create is not None:
                on_create(o)
        return o

    def get(self, name: str, on_surrogate: ty.Callable = _DO_NOTHING) -> VirtualF3Occurrence:
        if name in self:
            return self[name]
        o = self.new_surrogate(name, self.parent_occ)
        on_surrogate(o)
        return o

    def clear(self):
        if self.parent_comp is not None:
            for o in list(self.parent_comp.occurrences):
                o.deleteMe()
        self.surrogate_occs.clear()


class SurrogateComponent:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attr: ty.Dict[str, str] = {}
        get_context()._surrogate_comps[name] = self

    @staticmethod
    def get(name: str) -> 'SurrogateComponent':
        comps = get_context()._surrogate_comps
        if name in comps:
            return comps[name]
        return SurrogateComponent(name)

    def delete_me(self):
        del get_context()._surrogate_comps[self.name]

    @property
    def bRepBodies(self) -> af.BRepBodies:
        raise Exception('Bad code. This is a surrogate.')


class SurrogateF3Occurrence:
    def __init__(self, name: str, parent: VirtualF3Occurrence, transform: ac.Matrix3D = EYE_M3D, comp: ty.Optional[VirtualComponent] = None) -> None:
        if comp is None:
            _comp = SurrogateComponent.get(name)
            self.comp: VirtualComponent = _comp
            self.comp_attr: ty.Union[F3AttributeDict, ty.MutableMapping[str, str]] = _comp.attr
        else:
            if name != comp.name:
                raise Exception(f'Bad code. arg name: {name}  comp name: {comp.name}')
            self.comp: VirtualComponent = comp
            if isinstance(comp, SurrogateComponent):
                _attr = comp.attr
            else:
                _attr = F3AttributeDict(comp.attributes)
            self.comp_attr: ty.Union[F3AttributeDict, ty.MutableMapping[str, str]] = _attr
        self.parent = parent
        self.has_parent = True
        self.name = name
        self.child = F3OccurrenceDict(self)
        self.occ_attr: ty.MutableMapping[str, str] = {}
        self._transform = transform.copy()
        self.light_bulb = True
        self.rigid_in_replace = False

    def bodies_by_attr(self, attr_name: str, attr_value: ty.Optional[str] = None):
        raise Exception('This is a surrogate.')

    @property
    def raw_occ(self) -> af.Occurrence:
        raise Exception('This is a surrogate.')

    @property
    def transform(self):
        return self._transform.copy()
    
    @transform.setter
    def transform(self, transform: ac.Matrix3D):
        self._transform = transform.copy()

    def replace(self, on_create: ty.Callable = _DO_NOTHING, real_occ: ty.Optional['F3Occurrence'] = None):
        con = get_context()
        if not isinstance(self.parent, F3Occurrence):
            raise Exception('The parent is a surrogate.')
        self.parent.child.surrogate_occs.remove(self)

        if real_occ is not None:
            if real_occ.name != self.name:
                raise Exception('The move_comp.name should be the same with self.name.')
            new_occ = real_occ.move_to(self.parent, self.name)
        elif isinstance(self.comp, SurrogateComponent):
            new_comp = None
            for c in con.des.allComponents:
                if c.name == self.name:
                    new_comp = c
                    break
            capture_position()
            if new_comp is None:
                raw_occ = self.parent.raw_occ.component.occurrences.addNewComponent(EYE_M3D)
                raw_occ.component.name = self.name
                if raw_occ.component.name != self.name:
                    raise Exception(f'Name collision: {self.name} already exists.')
            else:
                raw_occ = self.parent.raw_occ.component.occurrences.addExistingComponent(new_comp, EYE_M3D)
            raw_occ = raw_occ.createForAssemblyContext(self.parent.raw_occ)
            new_occ = F3Occurrence(raw_occ)
        else:  # self.comp is af.Component
            capture_position()
            raw_occ = self.parent.raw_occ.component.occurrences.addExistingComponent(self.comp, EYE_M3D)
            raw_occ = raw_occ.createForAssemblyContext(self.parent.raw_occ)
            new_occ = F3Occurrence(raw_occ)

        for n, v in self.comp_attr.items():
            new_occ.comp_attr[n] = v
        for n, v in self.occ_attr.items():
            new_occ.occ_attr[n] = v

        for o in list(self.child.surrogate_occs):
            o.parent = new_occ
            o.replace()

        # This is a remedy to a bug of F360.
        pos = ORIGIN_P3D.copy()
        pos.transformBy(self.transform)
        last_distance = None
        while True:
            new_occ.transform = self.transform
            pos2 = ORIGIN_P3D.copy()
            pos2.transformBy(new_occ.transform)
            if pos2.isEqualToByTolerance(pos, 0.01):
                break
            d = pos2.distanceTo(pos)
            if last_distance is not None and d > last_distance and d > 0.1:
                con.ui.messageBox(
                    'Sorry, you came across a fatal bug of Fusion 360. \nhttps://forums.autodesk.com/t5/fusion-360-api-and-scripts/strange-behavior-of-occurrence-transform-when-it-was-assigned/m-p/10638077\n' +
                    'I could not find any workaround. There is nothing we can do about it. Ask Autodesk, at most.')
                break
            last_distance = d
            print('transform iteration...')

        new_occ.light_bulb = self.light_bulb

        if self.rigid_in_replace:
            new_occ.rigidize()

        on_create(new_occ)

        return new_occ


class F3Occurrence:
    def __init__(self, o: ty.Union[af.Occurrence, ac.Base]) -> None:
        if not isinstance(o, af.Occurrence):
            o = af.Occurrence.cast(o)
            if o is None:
                raise Exception('The arg is not af.Occurrence.')
        self.raw_occ = o
        self._child = F3OccurrenceDict(self)
        self._occ_attr = F3AttributeDict(self.raw_occ.attributes)
        self._comp_attr = F3AttributeDict(self.raw_occ.component.attributes)

    def move_to(self, new_parent_occ: 'F3Occurrence', name: str):
        if name in new_parent_occ.child:
            del new_parent_occ.child[name]
        capture_position()
        new_raw_occ = self.raw_occ.moveToComponent(new_parent_occ.raw_occ)
        new_raw_occ.component.name = name
        if new_raw_occ.component.name != name:
            raise Exception(f'Name collision: {name} already exists.')
        return F3Occurrence(new_raw_occ)

    def rigidize(self):
        oc = CreateObjectCollectionT(af.Occurrence)
        oc.add(self.parent.raw_occ)
        oc.add(self.raw_occ)
        capture_position()
        self.parent.comp.rigidGroups.add(oc, False)

    def bodies_by_attr(self, attr_name: str, attr_value: ty.Optional[str] = None):
        ret: ty.List[af.BRepBody] = []
        for b in self.raw_occ.component.bRepBodies:
            if b.nativeObject is not None:
                raise Exception('Bad code.')
            for a in b.attributes:
                if a.name == attr_name and (attr_value is None or a.value == attr_value):
                    ret.append(b.createForAssemblyContext(self.raw_occ))
                    continue
        return ret

    @property
    def name(self):
        return self.raw_occ.component.name

    @name.setter
    def name(self, name):
        self.raw_occ.component.name = name
        if self.raw_occ.component.name != name:
            raise Exception(f'{name} raises name collision. All components should have identical name.')

    @property
    def parent(self):
        return F3Occurrence(self.raw_occ.assemblyContext)

    @property
    def has_parent(self):
        return self.raw_occ.assemblyContext is not None

    @property
    def child(self):
        return self._child

    @property
    def comp(self):
        return self.raw_occ.component

    @property
    def occ_attr(self):
        return self._occ_attr

    @property
    def comp_attr(self):
        return self._comp_attr

    @property
    def light_bulb(self):
        return self.raw_occ.isLightBulbOn

    @light_bulb.setter
    def light_bulb(self, is_on: bool):
        self.raw_occ.isLightBulbOn = is_on

    @property
    def transform(self):
        return self.raw_occ.transform
    
    @transform.setter
    def transform(self, transform: ac.Matrix3D):
        self.raw_occ.transform = transform


class F3AttributeSingletonDict:
    def __init__(self, con: 'F3Context') -> None:
        self.con = con

    def __getitem__(self, name: str) -> ty.Tuple[str, ty.Any]:
        attrs = self.con.find_attrs(name)
        if len(attrs) == 0:
            raise KeyError(f'{name} not found.')
        elif len(attrs) > 1:
            raise KeyError(f'{name} is not singleton.')
        return attrs[0].value, attrs[0].parent

    def __setitem__(self, name: str, value: ty.Tuple[str, ty.Any]):
        s, e = value
        attrs = self.con.find_attrs(name)
        for a in attrs:
            a.deleteMe()
        e.attributes.add(ATTR_GROUP, name, s)

    def __delitem__(self, name: str):
        attrs = self.con.find_attrs(name)
        for a in attrs:
            a.deleteMe()

    def __contains__(self, name: str):
        return len(self.con.find_attrs(name)) > 0


def _get_occ_names(occ: VirtualF3Occurrence):
    occ_names = []
    o = occ
    while o.has_parent:
        occ_names.append(o.name)
        o = o.parent
    occ_names.append(o.name)
    return occ_names[::-1]


class SurrogateOccurrences(ty.Iterable[SurrogateF3Occurrence], ty.Sized):
    def __init__(self, parent_occ: VirtualF3Occurrence) -> None:
        self.parent_occ = parent_occ
        poc_names = _get_occ_names(parent_occ)
        con = get_context()
        if parent_occ.name not in con._comp_name_surrogate_child_names:
            con._comp_name_surrogate_child_names[parent_occ.name] = []
        self.child_names = con._comp_name_surrogate_child_names[parent_occ.name]
        for names, sos in con._poc_names_surrogate_occs:
            if names == poc_names:
                self.surrogate_occs = sos
                return
        sos: ty.List[SurrogateF3Occurrence] = []
        con._poc_names_surrogate_occs.append((poc_names, sos))
        self.surrogate_occs = sos

    def __iter__(self) -> ty.Iterator[SurrogateF3Occurrence]:
        for cn in self.child_names:
            hit = False
            for o in self.surrogate_occs:
                if o.name == cn:
                    hit = True
                    yield o
                    break
            if not hit:
                o = SurrogateF3Occurrence(cn, self.parent_occ)
                self.surrogate_occs.append(o)
                yield o

    def __len__(self) -> int:
        return len(self.child_names)

    def append(self, o: SurrogateF3Occurrence):
        self.child_names.append(o.name)
        self.surrogate_occs.append(o)

    def _remove_surrogate_comp(self, cn: str):
        con = get_context()
        for _, sos in con._poc_names_surrogate_occs:
            for so in sos:
                if so.name == cn:  # Reference exists.
                    return
        del con._comp_name_surrogate_child_names[cn]

    def remove(self, o: SurrogateF3Occurrence):
        self.child_names.remove(o.name)
        self.surrogate_occs.remove(o)
        self._remove_surrogate_comp(o.name)

    def clear(self):
        self.surrogate_occs.clear()
        for cn in self.child_names:
            self._remove_surrogate_comp(cn)
        self.child_names.clear()


class F3Context:
    stashed_transform: ty.Dict[str, ty.Tuple[ac.Matrix3D, ty.Dict]] = {}

    def __init__(self, des: ty.Optional[af.Design] = None) -> None:
        self.app = ac.Application.get()
        self.ui = self.app.userInterface
        self.des = af.Design.cast(self.app.activeProduct) if des is None else des
        self.root_comp = self.des.rootComponent
        self._child = F3OccurrenceDict(self.root_comp)
        self._comp_attr = F3AttributeDict(self.root_comp.attributes)
        self._attr_singleton = F3AttributeSingletonDict(self)
        self.prepare_parameter_dict: ty.Dict[str, ty.Dict] = defaultdict(dict)
        self._poc_names_surrogate_occs: ty.List[ty.Tuple[ty.List[str], ty.List[SurrogateF3Occurrence]]] = []
        self._comp_name_surrogate_child_names: ty.Dict[str, ty.List[str]] = {}
        self._surrogate_comps: ty.Dict[str, SurrogateComponent] = {}

    def clear_surrogate(self):
        self._poc_names_surrogate_occs.clear()
        self._comp_name_surrogate_child_names.clear()
        self._surrogate_comps.clear()

    @property
    def name(self):
        return self.root_comp.name

    @name.setter
    def name(self, name):
        self.root_comp.name = name
        if self.root_comp.name != name:  # name collision
            raise Exception(f'{name} raises name collision. All components should have identical name.')

    @property
    def child(self):
        return self._child

    @property
    def comp(self):
        return self.root_comp

    @property
    def id(self):
        return self.root_comp.id

    @property
    def comp_attr(self):
        return self._comp_attr

    def find_by_token(self, token: str):
        return list(self.des.findEntityByToken(token))

    def find_attrs(self, name: str):
        return self.des.findAttributes(ATTR_GROUP, name)

    @property
    def attr_singleton(self):
        return self._attr_singleton


F3_CONTEXT: ty.Optional[F3Context] = None


def get_context(des: ty.Optional[af.Design] = None):
    global F3_CONTEXT

    if des is not None:
        return F3Context(des)

    if F3_CONTEXT is None:
        F3_CONTEXT = F3Context()
    return F3_CONTEXT


def set_context(con: F3Context):
    global F3_CONTEXT

    F3_CONTEXT = con
    return con


def reset_context(des: ty.Optional[af.Design] = None):
    global F3_CONTEXT

    con = F3Context(des)
    F3_CONTEXT = con
    return con


def catch_exception(func: ty.Callable):
    '''
    This attribute wraps handlers which are called from F360 message pump.
    '''
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            adsk.terminate()
    return wrapped


def CreateObjectCollectionT(cls):
    r: ac.ObjectCollectionT[cls] = ac.ObjectCollection.create()  # type: ignore
    return r


def cap_placeholder_name(i: int, cap_desc: str, specifier: str, legend: ty.List[str]):
    hex_str = ' '.join(['0x' + x.encode().hex() for x in legend if x is not None])
    return f'{cap_desc} {specifier} {i} {hex_str}{CNP_CAP_PLACEHOLDER}'


def key_locator_name(i: int, pattern_name: str):
    return f'{pattern_name} {i}{CNP_KEY_LOCATOR}'


def key_placeholder_name(i: int, pattern_name: str):
    return f'{pattern_name} {i}{CNP_KEY_PLACEHOLDER}'


def key_assembly_name(specifier: str, cap_desc: str, stabilizer_desc: str, stabilizer_orientation_str: str, switch_desc: str, switch_orientation_str: str, align_to: str):
    return f'{cap_desc} {stabilizer_desc} {stabilizer_orientation_str} {switch_desc} {switch_orientation_str} {align_to} {specifier}{CNP_KEY_ASSEMBLY}'


def _part_name(desc: str, specifier: ty.Optional[str] = None):
    if specifier is None:
        return desc + CNP_PARTS
    else:
        return f'{desc} {specifier}{CNP_PARTS}'


def cap_name(cap_desc: str, specifier: str, parameters: ty.Dict[str, Quantity]):
    return _part_name('Cap ' + cap_desc, specifier + ' Travel ' + str(parameters['Travel']))


def stabilizer_name(stabilizer_desc: str, specifier: str, parameters: ty.Dict[str, Quantity]):
    return _part_name('Stabilizer ' + stabilizer_desc, ' '.join([k + ' ' + str(v) for k, v in parameters.items()]))


def switch_name(switch_desc: str, specifier: str, parameters: ty.Dict[str, Quantity]):
    return _part_name('Switch ' + switch_desc)


def pcb_name(switch_desc: str, specifier: str, parameters: ty.Dict[str, Quantity]):
    return _part_name('PCB ' + switch_desc)


def get_ids(comp: af.Component) -> ty.Set[str]:
    return set([o.component.id for o in comp.occurrences])


@contextmanager
def create_component(acc_comp: VirtualComponent, new_name: str, postfix: str = None):
    if isinstance(acc_comp, SurrogateComponent):
        raise Exception("SurrogateComponent is not available.")
    container: ty.List[F3Occurrence] = []
    before_ids = get_ids(acc_comp)
    yield container
    after_ids = get_ids(acc_comp)
    new_id = (after_ids - before_ids).pop()
    for o in acc_comp.occurrences:
        if o.component.id == new_id:
            o.component.name = new_name if postfix is None else new_name + postfix
            container.append(F3Occurrence(o))
            break


KLE_CACHE: ty.Dict[str, ty.Any] = {}


def load_kle(kle_file: pathlib.Path, pi: parts_resolver.PartsInfo) -> ty.Tuple[SpecsOpsOnPn, ty.Tuple, ty.Tuple]:
    with open(kle_file, 'rb') as f:
        kle_file_content = f.read()
    kle_hash = hashlib.md5(kle_file_content).hexdigest()
    if kle_hash in KLE_CACHE:
        return KLE_CACHE[kle_hash]

    try:
        result = pi.resolve_kle(kle_file, CURRENT_DIR / 'tmp')
        KLE_CACHE[kle_hash] = result
        specs_ops_on_pn, min_xyu, max_xyu = result
    except Exception as e:
        msg = str(e)
        if msg.startswith('Failed to load'):
            # PC's hibernate -> resume often raises this error. F360's Python's problem.
            pass
        else:
            print(f'resolve_kle() Failed. The error message:\n{str(e)}\n\nTry again...', file=sys.stderr)
        specs_ops_on_pn, min_xyu, max_xyu = pi.resolve_kle(kle_file, CURRENT_DIR / 'tmp')

    return specs_ops_on_pn, min_xyu, max_xyu


def load_kle_by_b64(kle_b64: str, pi: parts_resolver.PartsInfo):
    kle_file_content = zlib.decompress(base64.b64decode(kle_b64))
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        fp = pathlib.Path(d) / 'temp.json'
        with open(fp, 'w+b') as f:
            f.write(kle_file_content)
        return load_kle(fp, pi)


def get_parts_data_path():
    return pathlib.Path(get_context().child[CN_INTERNAL].comp_attr[AN_PARTS_DATA_PATH])


def get_part_info():
    return parts_resolver.PartsInfo(get_parts_data_path() / parts_resolver.PARTS_INFO_DIRNAME)


from time import perf_counter


@dataclass(eq=True, frozen=True)
class Segment:
    filename: str
    lineno: int


class Profiler:
    def __init__(self) -> None:
        self.last = perf_counter()
        fs = traceback.extract_stack(limit=2)[0]
        self.last_segment = Segment(fs.filename, fs.lineno)
        self.log: ty.Dict[ty.Tuple[Segment, Segment], float] = defaultdict(lambda: 0.)

    def reset(self):
        self.last = perf_counter()
        fs = traceback.extract_stack(limit=2)[0]
        self.last_segment = Segment(fs.filename, fs.lineno)
        self.log.clear()

    def tick(self):
        now = perf_counter()
        fs = traceback.extract_stack(limit=2)[0]
        segment = Segment(fs.filename, fs.lineno)
        t = now - self.last
        self.log[(self.last_segment, segment)] += t
        self.last = now
        self.last_segment = segment

    def seg_to_str(self, s: Segment):
        return f'File "{s.filename}", line {s.lineno}'

    def get_log(self):
        ret = ''
        for segments, t in self.log.items():
            s = self.seg_to_str(segments[0]) + ' to ' + self.seg_to_str(segments[1]) + '\n' + f'    Time: {t:.2f}\n'
            ret += s

        return ret


PROF = Profiler()
