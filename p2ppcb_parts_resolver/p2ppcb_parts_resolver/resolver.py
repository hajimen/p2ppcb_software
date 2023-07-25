import functools
from collections import defaultdict
import os
import pathlib
import re
from enum import Enum, auto
import csv
from dataclasses import dataclass
import typing as ty
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import pint.errors
from pint import Quantity
from PIL import Image

DESCRIPTION_FILENAME = 'description.csv'
MAPPING_FILENAME = 'mapping.csv'
AVAILABLE_FILENAME = 'available.txt'
PARTS_INFO_DIRNAME = 'parameters'

# SPN: Special Parameter Name
SPN_SWITCH_ANGLE = 'SwitchAngle'
SPN_SWITCH_X = 'SwitchX'
SPN_SWITCH_Y = 'SwitchY'
SPN_STABILIZER_ANGLE = 'StabilizerAngle'
SPN_STABILIZER_X = 'StabilizerX'
SPN_STABILIZER_Y = 'StabilizerY'

SPN_TRAVEL = 'Travel'
SPN_STABILIZER_TRAVEL = 'StabilizerTravel'
SPN_TOP_HEIGHT = 'TopHeight'
SPN_CAP_SB_HEIGHT = 'CapStemBottomHeight'
SPN_SWITCH_SB_HEIGHT = 'SwitchStemBottomHeight'
SPN_STABILIZER_SB_HEIGHT = 'StabilizerStemBottomHeight'
SPN_SWITCH_BOTTOM_HEIGHT = 'SwitchBottomHeight'

SpecsOpsOnPn = ty.Dict[str, ty.List[ty.Tuple[str, ty.Optional['OccurrenceParameter']]]]

# import traceback
# from time import perf_counter


# @dataclass(eq=True, frozen=True)
# class Segment:
#     filename: str
#     lineno: int


# class Profiler:
#     def __init__(self) -> None:
#         self.last = perf_counter()
#         fs = traceback.extract_stack(limit=2)[0]
#         self.last_segment = Segment(fs.filename, fs.lineno)
#         self.log: ty.Dict[ty.Tuple[Segment, Segment], float] = defaultdict(lambda: 0.)

#     def reset(self):
#         self.last = perf_counter()
#         fs = traceback.extract_stack(limit=2)[0]
#         self.last_segment = Segment(fs.filename, fs.lineno)
#         self.log.clear()

#     def tick(self):
#         now = perf_counter()
#         fs = traceback.extract_stack(limit=2)[0]
#         segment = Segment(fs.filename, fs.lineno)
#         t = now - self.last
#         self.log[(self.last_segment, segment)] += t
#         self.last = now
#         self.last_segment = segment

#     def seg_to_str(self, s: Segment):
#         return f'File "{s.filename}", line {s.lineno}'

#     def get_log(self):
#         ret = ''
#         for segs, t in self.log.items():
#             s = self.seg_to_str(segs[0]) + ' to ' + self.seg_to_str(segs[1]) + '\n' + f'    Time: {t:.2f}\n'
#             ret += s

#         return ret


# PROF = Profiler()


def _key_area_pattern(a: ty.List):
    x = np.array(a)
    for i in range(1, 50):
        if np.all((x >> i) == 0):
            return np.unpackbits(np.array(a, '>i8').view(np.uint8), axis=1)[:, -i:].astype(np.bool_)
    raise Exception(f'Bad argument:{a}')


_TRAILING_ZEROS_REGEX = re.compile(r'(\d*)\.?([1-9]{0,2}).*')


def width_u_to_str(f: float):
    return _TRAILING_ZEROS_REGEX.sub(r'\1\2', str(f)) + 'u'


KEY_AREA_PATTERN_DIC = {
    'ISO_Enter': _key_area_pattern([
        [0b111111],
        [0b111111],
        [0b111111],
        [0b111111],
        [0b011111],
        [0b011111],
        [0b011111],
        [0b011111],
    ]),
    'Bigass_Enter': _key_area_pattern([
        [0b000111111],
        [0b000111111],
        [0b000111111],
        [0b000111111],
        [0b111111111],
        [0b111111111],
        [0b111111111],
        [0b111111111],
    ]),
}
KEY_AREA_PATTERN_DIC.update({
    width_u_to_str(w / 4):
        _key_area_pattern([[(1 << w) - 1]] * 4)
        for w in list(range(4, 49))
})


class Part(Enum):
    Cap = auto()
    Stabilizer = auto()
    Switch = auto()
    PCB = auto()
    Decal = auto()
    Wiring = auto()


PARTS_WITH_COMPONENT = [Part.Cap, Part.Stabilizer, Part.Switch, Part.PCB]


def part_from_name(name: str):
    for p in Part:
        if p.name == name:
            return p
    raise Exception(f"Not found: {name} is not Part's name.")


@dataclass
class OccurrenceParameter:
    center_xyu: ty.Tuple[float, float]
    image_center_offset_u: ty.Tuple[float, float]
    image_whu: ty.Tuple[float, float]
    angle: float  # clockwise
    legend: ty.List[str]
    image_file_path: ty.Optional[pathlib.Path]
    i_kle: int


class AlignTo(Enum):
    StemBottom = auto()
    TravelBottom = auto()


@dataclass
class _MappingRow:
    specifier_pattern: re.Pattern
    filename: str
    parameter_names: ty.List[str]


class SpecifierException(Exception):
    def __init__(self, available_specifiers: ty.List[str], missed_specifier: str) -> None:
        super().__init__()
        self.available_specifiers = available_specifiers
        self.missed_specifier = missed_specifier


class ResolveParameterException(Exception):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path


class PartsInfo:
    def __init__(self, parts_info_dir: ty.Union[os.PathLike, str]):
        self.parts_info_dir = pathlib.Path(parts_info_dir)
        if not self.parts_info_dir.is_dir():
            raise Exception(f'Wrong path: {parts_info_dir} is not a directory.')
        if not (self.parts_info_dir / DESCRIPTION_FILENAME).exists():
            raise Exception(f'Wrong path: {parts_info_dir} doesn\'t have {DESCRIPTION_FILENAME}.')

        self.description_dict: ty.Dict[Part, ty.List[ty.Tuple[str, str]]] = defaultdict(list)  # {Part.Cap: [], Part.Stabilizer: [], Part.Switch: [], Part.PCB: [], Part.Decal: [], Part.Wiring: []}
        with open(self.parts_info_dir / DESCRIPTION_FILENAME, newline='') as f:
            d = csv.reader(f, delimiter=",", doublequote=True, quotechar='"', skipinitialspace=True)
            for i, row in enumerate(d):
                if i == 0:
                    if ','.join(row) != 'Part,Description,Path':
                        raise Exception(f'Wrong file: {DESCRIPTION_FILENAME} has wrong header.')
                else:
                    p = part_from_name(row[0])
                    self.description_dict[p].append((row[1], row[2]))

    def enumerate_description(self, part: Part):
        ret: ty.List[str] = []
        for d, _ in self.description_dict[part]:
            ret.append(d)
        return ret

    def resolve_decal(self, specifier: str, decal_desc: str):
        _, decal_parameter_names, path = self._resolve_parameters(specifier, decal_desc, Part.Decal)
        ps, _ = self._collect_parameters(specifier, path, {})
        try:
            parameters: ty.Dict[str, Quantity] = {n: Quantity(v) for n, v in ps.items()}  # type: ignore
        except pint.errors.UndefinedUnitError as pe:
            raise Exception('Bad value in parts info:' + str(pe))
        decal_parameters: ty.Dict[str, Quantity] = {}
        for n in set(decal_parameter_names) & set(parameters.keys()):
            decal_parameters[n] = parameters[n]
        return decal_parameters

    def resolve_pcb_wiring(self, specifier: str, switch_desc: str):
        filename, parameter_names, path = self._resolve_parameters(specifier, switch_desc, Part.Wiring)
        ps, _ = self._collect_parameters(specifier, path, {})
        try:
            parameters: ty.Dict[str, Quantity] = {n: Quantity(v) for n, v in ps.items()}  # type: ignore
        except pint.errors.UndefinedUnitError as pe:
            raise Exception('Bad value in parts info:' + str(pe))
        wiring_parameters: ty.Dict[str, Quantity] = {}
        for n in set(parameter_names) & set(parameters.keys()):
            wiring_parameters[n] = parameters[n]
        return filename, wiring_parameters

    @functools.lru_cache(maxsize=None)
    def read_splitlines_file(self, file: os.PathLike) -> ty.List[str]:
        with open(file) as f:
            return list(f.read().splitlines())

    def resolve_specifier(
        self, specifier: str, cap_desc: str, stabilizer_desc: str, switch_desc: str, align_to: AlignTo
    ) -> ty.Tuple[ty.Dict[Part, str], ty.Dict[Part, ty.Dict[str, Quantity]], ty.Dict[Part, str], ty.Dict[Part, Quantity], ty.Dict[str, Quantity]]:
        parameters: ty.Dict[str, Quantity] = {}
        part_filename: ty.Dict[Part, str] = {}
        part_parameter_names: ty.Dict[Part, ty.List[str]] = {}
        part_placeholder: ty.Dict[Part, str] = {}
        part_height_parameter: ty.Dict[Part, ty.Dict[str, Quantity]] = {}
        switch_xya: ty.Dict[str, Quantity] = {
            SPN_SWITCH_ANGLE: Quantity('0 deg'), SPN_SWITCH_X: Quantity('0 mm'), SPN_SWITCH_Y: Quantity('0 mm'),
            SPN_STABILIZER_ANGLE: Quantity('0 deg'), SPN_STABILIZER_X: Quantity('0 mm'), SPN_STABILIZER_Y: Quantity('0 mm')}  # type: ignore
        for desc, part in [(cap_desc, Part.Cap), (stabilizer_desc, Part.Stabilizer), (switch_desc, Part.Switch), (switch_desc, Part.PCB)]:
            try:
                part_filename[part], part_parameter_names[part], path = self._resolve_parameters(specifier, desc, part)
            except ResolveParameterException as e:
                if part == Part.Cap:
                    raise SpecifierException(self.read_splitlines_file(self.parts_info_dir / e.path / AVAILABLE_FILENAME), specifier)
                else:
                    raise Exception(f'Wrong specifier: {specifier}')
            if part == Part.Cap:
                available = False
                lines = []
                for line in self.read_splitlines_file(self.parts_info_dir / path / AVAILABLE_FILENAME):
                    lines.append(line)
                    if re.match(r'^' + line + r'$', specifier) is not None:
                        available = True
                        break
                if not available:
                    raise SpecifierException(lines, specifier)
            ps, ph = self._collect_parameters(specifier, path, {})
            part_placeholder[part] = ph
            try:
                qps: ty.Dict[str, Quantity] = {n: Quantity(v) for n, v in ps.items()}  # type: ignore
            except pint.errors.UndefinedUnitError as pe:
                raise Exception('Bad value in parts info:' + str(pe))
            for n in [SPN_CAP_SB_HEIGHT, SPN_SWITCH_SB_HEIGHT, SPN_STABILIZER_SB_HEIGHT, SPN_SWITCH_BOTTOM_HEIGHT]:
                if n in qps:
                    if part not in part_height_parameter:
                        part_height_parameter[part] = {}
                    part_height_parameter[part][n] = qps.pop(n)
            for n in [SPN_SWITCH_ANGLE, SPN_SWITCH_X, SPN_SWITCH_Y, SPN_STABILIZER_ANGLE, SPN_STABILIZER_X, SPN_STABILIZER_Y]:
                if n in qps:
                    v = qps.pop(n)
                    if part == Part.Cap:
                        switch_xya[n] = v
            parameters.update(qps)

        for n, p in [(SPN_CAP_SB_HEIGHT, Part.Cap), (SPN_SWITCH_SB_HEIGHT, Part.Switch),
                     (SPN_SWITCH_BOTTOM_HEIGHT, Part.Switch), (SPN_STABILIZER_SB_HEIGHT, Part.Stabilizer)]:
            if p not in part_height_parameter or n not in part_height_parameter[p]:
                raise Exception(f'Parts info lacks mandatory parameter: {n} about {p.name} of {cap_desc}, {stabilizer_desc}, {switch_desc}.')
        for n, p in [(SPN_TOP_HEIGHT, Part.Cap), (SPN_TRAVEL, Part.Switch), (SPN_STABILIZER_TRAVEL, Part.Stabilizer)]:
            if n not in parameters:
                raise Exception(f'Parts info lacks mandatory parameter: {n} about {p.name} of {cap_desc}, {switch_desc}.')
        travel_gap = parameters[SPN_STABILIZER_TRAVEL] - parameters[SPN_TRAVEL]
        part_z_pos: ty.Dict[Part, Quantity] = {
            Part.Cap: - part_height_parameter[Part.Cap][SPN_CAP_SB_HEIGHT],
            Part.Stabilizer: - part_height_parameter[Part.Stabilizer][SPN_STABILIZER_SB_HEIGHT] + travel_gap,
            Part.Switch: - part_height_parameter[Part.Switch][SPN_SWITCH_SB_HEIGHT],
            Part.PCB: - part_height_parameter[Part.Switch][SPN_SWITCH_SB_HEIGHT] + part_height_parameter[Part.Switch][SPN_SWITCH_BOTTOM_HEIGHT],
        }  # type: ignore
        if align_to == AlignTo.TravelBottom:
            for p in part_z_pos.keys():
                part_z_pos[p] += part_height_parameter[Part.Cap][SPN_CAP_SB_HEIGHT] + parameters[SPN_TRAVEL] - parameters[SPN_TOP_HEIGHT]  # type: ignore

        part_parameters: ty.Dict[Part, ty.Dict[str, Quantity]] = {}
        for part in PARTS_WITH_COMPONENT:
            part_parameters[part] = {}
            for n in set(part_parameter_names[part]) & set(parameters.keys()):
                part_parameters[part][n] = parameters[n]

        return part_filename, part_parameters, part_placeholder, part_z_pos, switch_xya

    def _read_mapping_from_desc(self, desc: str, part: Part) -> ty.Tuple[ty.List[_MappingRow], str]:
        for d, path in self.description_dict[part]:
            if d == desc:
                mapping: ty.List[_MappingRow] = []
                with open(self.parts_info_dir / path / MAPPING_FILENAME) as f:
                    m = csv.reader(f, delimiter=",", doublequote=True, quotechar='"', skipinitialspace=True)
                    for i, row in enumerate(m):
                        if i == 0:
                            if ','.join(row) != 'Specifier,filename,Parameter':
                                raise Exception(f'Wrong file: {MAPPING_FILENAME} has wrong header.')
                        else:
                            mapping.append(_MappingRow(re.compile(row[0]), row[1], row[2].split()))
                return mapping, path
        raise Exception(f'Wrong description: {desc} about part: {part.name}')

    @functools.lru_cache(maxsize=None)
    def _resolve_parameters(self, specifier: str, desc: str, part: Part):
        mapping, path = self._read_mapping_from_desc(desc, part)
        for m in mapping:
            if m.specifier_pattern.search(specifier) is not None:
                return m.filename, m.parameter_names, path
        raise ResolveParameterException(path)

    @functools.lru_cache(maxsize=None)
    def _list_csv_files(self, path: str) -> ty.List[ty.Tuple[str, ty.List[ty.List[str]]]]:
        ret: ty.List[ty.Tuple[str, ty.List[ty.List[str]]]] = []
        for p in (self.parts_info_dir / path).iterdir():
            if p.is_file() and p.suffix == '.csv' and p.name != MAPPING_FILENAME and p.name != DESCRIPTION_FILENAME:
                with open(p) as f:
                    reader = csv.reader(f, delimiter=",", doublequote=True, quotechar='"', skipinitialspace=True)
                    ret2: ty.List[ty.List[str]] = []
                    for row in reader:
                        ret2.append(list(row))
                    ret.append((str(p), ret2))
        return ret

    def _collect_parameters_rec(self, specifier: str, path: str, parameters: ty.Dict[str, str]) -> ty.Dict[str, str]:
        for p, reader in self._list_csv_files(path):
            pns = []
            for i, row in enumerate(reader):
                if i == 0:
                    if row[0] != 'Specifier':
                        raise Exception(f'Wrong file: {p} has wrong header.')
                    pns = row
                else:
                    if re.search(r'\b' + row[0] + r'\b', specifier) is not None:
                        for n, v in zip(pns[1:], row[1:]):
                            if n not in parameters:
                                parameters[n] = v
                        break
        if path != '':
            parent, _ = os.path.split(path)
            return self._collect_parameters_rec(specifier, parent, parameters)
        else:
            return parameters

    def _collect_parameters(self, specifier: str, path: str, parameters: ty.Dict[str, str]) -> ty.Tuple[ty.Dict[str, str], str]:
        parameters = self._collect_parameters_rec(specifier, path, parameters)
        ph = 'Placeholder'
        if 'Placeholder' in parameters:
            ph = parameters.pop('Placeholder')
        return parameters, ph

    def resolve_kle(self, kle_json_path: os.PathLike, image_output_dir: ty.Optional[os.PathLike]):
        image_output_dir = None if image_output_dir is None else pathlib.Path(image_output_dir)
        # op: OccurrenceParameter, pn: pattern name
        specs_ops_on_pn: SpecsOpsOnPn = defaultdict(list)
        vertices: ty.Set[ty.Tuple[float, float]] = set()

        if image_output_dir is None:
            import pykle_serial as kle_serial
            with open(kle_json_path, 'r', encoding='utf-8') as f:
                json = f.read()
            keyboard = kle_serial.parse(json)
        else:
            from kle_scraper import scrape
            keyboard = scrape(kle_json_path, image_output_dir)
        if keyboard is None:
            raise Exception('Bad KLE file or image_output_dir.')
        for i, k in enumerate(keyboard.keys):
            inner_vertices: ty.Set[ty.Tuple[float, float]] = set()

            def _add_inner_vertex(x: float, y: float, w: float, h: float):
                inner_vertices.add((x, y))
                inner_vertices.add((x + w, y))
                inner_vertices.add((x + w, y + h))
                inner_vertices.add((x, y + h))

            specs: ty.List[str] = []
            pattern_rotation = None
            center_xu = 0  # unit
            center_yu = 0  # unit
            image_center_offset_u = (0., 0.)  # unit
            image_whu = (0., 0.)  # unit
            if len(k.profile) > 0:
                specs.append(k.profile)
            if k.stepped:
                specs.append('Stepped')
            wh = sorted([k.width, k.height])
            if wh[0] == 1 and k.width2 == k.width and k.height == k.height2 and k.x2 == 0 and k.y2 == 0:
                if k.height > k.width:
                    pattern_rotation = Image.ROTATE_90
                w = wh[1]
                if w == 1:
                    if k.nub:
                        specs.append('Homing')
                if w >= 5:
                    specs.append('Spacebar')
                pattern_name = width_u_to_str(w)
                specs.append(pattern_name)

                center_xu = k.x + k.width / 2
                center_yu = k.y + k.height / 2
                image_center_offset_u = (0., 0.)
                _add_inner_vertex(k.x, k.y, k.width, k.height)
            else:
                AREA_SIZE = 64
                AREA_CENTER = AREA_SIZE // 2
                area = np.zeros([AREA_SIZE, AREA_SIZE], np.bool_)
                area[AREA_CENTER: AREA_CENTER + round(k.height * 4), AREA_CENTER:AREA_CENTER + round(k.width * 4)] = True
                area[AREA_CENTER + round(k.y2 * 4): AREA_CENTER + round((k.height2 + k.y2) * 4),
                     AREA_CENTER + round(k.x2 * 4):AREA_CENTER + round((k.width2 + k.x2) * 4)] = True

                def _find():
                    for pattern_name, pattern in KEY_AREA_PATTERN_DIC.items():
                        rp = pattern
                        for r in [None, Image.ROTATE_270, Image.ROTATE_180, Image.ROTATE_90]:
                            hit = np.all(sliding_window_view(area, rp.shape) == rp, (2, 3))
                            if np.any(hit):
                                hit_iy, hit_ix = np.argwhere(hit)[0]
                                ca = np.copy(area)
                                ca[hit_iy:hit_iy + rp.shape[0], hit_ix:hit_ix + rp.shape[1]] = False
                                if np.any(ca):
                                    continue
                                y, x = (np.argwhere(hit)[0] - AREA_CENTER) / 4
                                h = rp.shape[0] / 4
                                w = rp.shape[1] / 4
                                _add_inner_vertex(k.x + x, k.y + y, w, h)
                                center_xu = k.x + x + w / 2
                                center_yu = k.y + y + h / 2
                                return pattern_name, r, (center_xu, center_yu), (k.x + k.width / 2 - center_xu, k.y + k.height / 2 - center_yu)
                            rp = np.rot90(rp)
                    raise Exception(f'Invalid key form: w:{k.width} w2:{k.width2} h:{k.height} h2:{k.height2} x:{k.x} y:{k.y} x2:{k.x2} y2:{k.y2} is invalid.')

                pattern_name, pattern_rotation, (center_xu, center_yu), image_center_offset_u = _find()
                specs = [pattern_name]
            image_whu = (k.width, k.height)
            image_path = None if image_output_dir is None else image_output_dir / f'{i}.png'
            angle = k.rotation_angle  # clockwise degree
            if pattern_rotation is not None:
                if image_path is not None:
                    image = Image.open(image_path)
                    image = image.transpose(pattern_rotation)
                    image.save(image_path)
                angle += {Image.ROTATE_270: -90, Image.ROTATE_180: 180, Image.ROTATE_90: 90}[pattern_rotation]
                rot_mat = np.array({
                    Image.ROTATE_90: [[0., 1.], [-1., 0.]],
                    Image.ROTATE_180: [[-1., 0.], [0., -1.]],
                    Image.ROTATE_270: [[0., -1.], [1., 0.]],
                }[pattern_rotation])
                image_center_offset_u = ty.cast(ty.Tuple[float, float], tuple(rot_mat @ np.array(image_center_offset_u)))
                image_whu = image_whu if pattern_rotation == Image.ROTATE_180 else (image_whu[1], image_whu[0])
            if k.rotation_angle != 0:
                orig_mat = np.array([[1., 0., -k.rotation_x], [0., 1., -k.rotation_y], [0., 0., 1.]])
                trans_mat = np.array([[1., 0., k.rotation_x], [0., 1., k.rotation_y], [0., 0., 1.]])
                r = k.rotation_angle * np.pi / 180
                rot_mat = np.array([[np.cos(r), -np.sin(r), 0.], [np.sin(r), np.cos(r), 0.], [0., 0., 1.]])
                center_xu, center_yu, _ = trans_mat @ rot_mat @ orig_mat @ np.array([center_xu, center_yu, 1.])
                for vx, vy in inner_vertices:
                    rvx, rvy, _ = trans_mat @ rot_mat @ orig_mat @ np.array([vx, vy, 1.])
                    vertices.add((rvx, rvy))
            else:
                vertices |= inner_vertices
            op = OccurrenceParameter((center_xu, center_yu), image_center_offset_u, image_whu, angle, k.labels, image_path, i)
            specifier = ' '.join(specs)
            specs_ops_on_pn[pattern_name].append((specifier, op))
        vs = np.array(list(vertices))
        return specs_ops_on_pn, tuple(np.min(vs, axis=0)), tuple(np.max(vs, axis=0))
