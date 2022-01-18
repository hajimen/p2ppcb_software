import importlib
import re
from itertools import product
from collections import defaultdict
from enum import Enum, IntEnum, auto
from dataclasses import dataclass, field
import typing as ty

import mip
from PIL import Image, ImageDraw, ImageOps, ImageFont
import numpy as np
from p2ppcb_composer.cmd_common import AN_MAINBOARD
from route import dubins
from f360_common import AN_ROW_NAME, AN_SWITCH_DESC, AN_SWITCH_ORIENTATION, CN_INTERNAL, CN_KEY_LOCATORS, CNP_PARTS, \
    get_context, key_locator_name, load_kle_by_b64, get_part_info, get_parts_data_path, AN_KEY_PITCH, FourOrientation, AN_KLE_B64


WIRE_PITCH = 0.127
I_CODE_LABEL = 9
CURVATURE = 5


ROT_RAD: ty.Dict[FourOrientation, float] = {
    FourOrientation.Front: 0.,
    FourOrientation.Back: np.deg2rad(180),
    FourOrientation.Left: np.deg2rad(-90),
    FourOrientation.Right: np.deg2rad(90)
}


class TerminalDirection(Enum):
    Left = auto()
    Right = auto()


VertexType = ty.Tuple[int, TerminalDirection]
START: VertexType = (-1, TerminalDirection.Left)
Line = ty.List[VertexType]


class RC(IntEnum):
    Row = 0
    Col = 1


WirePath = ty.Tuple[float, float, float]  # x, y, angle
SwitchPath = ty.Dict[RC, ty.Dict[TerminalDirection, WirePath]]


@dataclass
class Entry:
    x: float
    y: float
    angle: float
    pin_number: int
    logical_number: int


@dataclass
class Key:
    key_location: ty.Tuple[float, float, float]  # x, y, angle
    switch_orientation: FourOrientation
    path: SwitchPath
    img: Image = field(compare=False)
    code: str
    i_row: int
    i_col: int
    i_logical_row: int
    i_logical_col: int


@dataclass
class WireGroup:
    start: int
    end: int
    logical_start: int
    rc: RC
    led: bool


def _get_rot(angle):
    return np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])


class FlatCable:
    WIRE_NAME_N_RE = re.compile(r'.+?(\d+)$')

    def __init__(self, n_wire: int, first_index_in_wire_name: int) -> None:
        self.n_wire = n_wire
        self.groups: ty.List[WireGroup] = []
        self.first_index_in_wire_name = first_index_in_wire_name

    def add_group(self, wire_group: WireGroup):
        self.groups.append(wire_group)

    def get_entries(self, angle: float, flip: bool, rc: RC, origin_xy: ty.Tuple[float, float]):  # angle==0 flip==False: cable aligns to vertical. The top is 1 pin. Entry direction is right.
        pos = []
        nps = []
        nls = []
        for g in self.groups:
            if g.rc == rc:
                for i in range(g.start, g.end):
                    pos.append((0., i * WIRE_PITCH * (-1 if flip else 1)))
                    nps.append(i + 1)
                    nls.append(g.logical_start + i)
        pos = np.array(pos)
        entries: ty.List[Entry] = []
        center_p = np.array([0., self.n_wire * WIRE_PITCH * (-1 if flip else 1) / 2])
        origin = np.array(origin_xy)
        for p, pn, ln in zip(pos, nps, nls):
            rp = ((p - center_p) @ _get_rot(angle)) + origin
            entries.append(Entry(rp[0], rp[1], angle, pn, ln))
        return entries

    def _get_group(self, wire_name: str, rc: RC):
        led = 'LED' in wire_name
        m = FlatCable.WIRE_NAME_N_RE.match(wire_name)
        if m is None:
            raise Exception(f"wire_name: {wire_name} lacks number.")
        i_in_group = int(m.group(1)) - self.first_index_in_wire_name
        for g in self.groups:
            if g.rc == rc and g.led == led:
                if i_in_group < g.end - g.start:
                    return i_in_group, g
        return None

    def get_pin_number(self, wire_name: str, rc: RC):
        ret = self._get_group(wire_name, rc)
        if ret is None:
            return None
        i_in_group, g = ret
        return g.start + i_in_group

    def get_logical_number(self, wire_name: str, rc: RC):
        ret = self._get_group(wire_name, rc)
        if ret is None:
            return None
        i_in_group, g = ret
        return g.logical_start + i_in_group


@dataclass
class FlatCablePlacement:
    flip: bool  # True: descending order at FourOrientation.Left
    orientation: FourOrientation
    cable: FlatCable


def _get_key_angle(k: Key):
    return k.key_location[2] + ROT_RAD[k.switch_orientation]


def _get_absolute_wire_path(key: Key, rc: RC, td: TerminalDirection, is_orig: bool) -> ty.Tuple[float, float, float]:
    wp = key.path[rc][td]
    key_angle = _get_key_angle(key)
    wp_loc = np.array(wp[:2])
    wp_angle = wp[2] - key_angle
    if is_orig:
        wp_angle = wp_angle + np.deg2rad(180.)
    ret = (wp_loc @ _get_rot(key_angle)) + np.array(key.key_location[:2])
    return ret[0], ret[1], wp_angle


def _make_dist_map(keys: ty.List[Key], rc: RC, entry: Entry):
    dist_map: ty.Dict[ty.Tuple[VertexType, VertexType], float] = {}
    v = set(range(len(keys)))

    for n, m in product(v, v):
        if n != m:
            for otd, dtd in product(TerminalDirection, TerminalDirection):
                orig_wire_path = _get_absolute_wire_path(keys[n], rc, otd, True)
                dest_wire_path = _get_absolute_wire_path(keys[m], rc, dtd, False)
                _, _, _, _, lengths = dubins.dubins_path_planning(orig_wire_path[0], orig_wire_path[1], orig_wire_path[2], dest_wire_path[0], dest_wire_path[1], dest_wire_path[2], CURVATURE)
                dist_map[(n, otd), (m, dtd)] = sum(lengths)

    for n, td in product(v, TerminalDirection):
        dest_wire_path = _get_absolute_wire_path(keys[n], rc, td, False)
        _, _, _, _, lengths = dubins.dubins_path_planning(entry.x, entry.y, entry.angle, dest_wire_path[0], dest_wire_path[1], dest_wire_path[2], CURVATURE)
        dist_map[START, (n, td)] = sum(lengths)

    return dist_map


def generate_route(matrix: ty.Dict[str, ty.Dict[str, str]], cable_placements: ty.List[FlatCablePlacement]):
    reverse_matrix: ty.Dict[str, ty.Tuple[str, str]] = {}
    for row_name, col_dic in matrix.items():
        for col_name, kl_name in col_dic.items():
            reverse_matrix[kl_name] = (row_name, col_name)

    con = get_context()
    inl_occ = con.child[CN_INTERNAL]
    locators_occ = inl_occ.child[CN_KEY_LOCATORS]
    part_data_path = get_parts_data_path()
    pi = get_part_info()
    kle_b64 = con.child[CN_INTERNAL].comp_attr[AN_KLE_B64]
    specs_ops_on_pn, min_xyu, max_xyu = load_kle_by_b64(kle_b64, pi)
    pitch = float(inl_occ.comp_attr[AN_KEY_PITCH])
    keys_row: ty.Dict[int, ty.List[Key]] = defaultdict(list)
    keys_col: ty.Dict[int, ty.List[Key]] = defaultdict(list)
    image_cache = {}
    for pattern_name, specs_ops in specs_ops_on_pn.items():
        for i, (specifier, op) in enumerate(specs_ops):
            if op is None:
                raise Exception('Bad code.')
            kl_name = key_locator_name(i, pattern_name)
            kl_occ = locators_occ.child[kl_name]
            switch_desc = kl_occ.comp_attr[AN_SWITCH_DESC]
            orientation = FourOrientation[kl_occ.comp_attr[AN_SWITCH_ORIENTATION]]
            code = op.legend[I_CODE_LABEL]
            if kl_occ.comp_attr[AN_ROW_NAME].startswith('LED'):
                specifier += ' LED'
            filename, wiring_parameters = pi.resolve_pcb_wiring(specifier, switch_desc)
            wp = {k: v.m_as('rad') if k.endswith('Angle') else v.m_as('cm') for k, v in wiring_parameters.items()}
            if filename in image_cache:
                img = image_cache[filename]
            else:
                img = Image.open(str(part_data_path / ('png/' + filename)))
                image_cache[filename] = img
            switch_path: SwitchPath = {
                RC.Col: {
                    TerminalDirection.Right: (wp['Col_R_X'], wp['Col_R_Y'], wp['Col_R_Angle']),
                    TerminalDirection.Left: (wp['Col_L_X'], wp['Col_L_Y'], wp['Col_L_Angle']),
                },
                RC.Row: {
                    TerminalDirection.Right: (wp['Row_R_X'], wp['Row_R_Y'], wp['Row_R_Angle']),
                    TerminalDirection.Left: (wp['Row_L_X'], wp['Row_L_Y'], wp['Row_L_Angle']),
                }
            }
            row_name, col_name = reverse_matrix[kl_name]
            i_pin_row = None
            i_logical_row = None
            cp_row = None
            i_pin_col = None
            i_logical_col = None
            cp_col = None
            for cp in cable_placements:
                if i_pin_row is None:
                    i_pin_row = cp.cable.get_pin_number(row_name, RC.Row)
                    cp_row = cp
                if i_logical_row is None:
                    i_logical_row = cp.cable.get_logical_number(row_name, RC.Row)
                if i_pin_col is None:
                    i_pin_col = cp.cable.get_pin_number(col_name, RC.Col)
                    cp_col = cp
                if i_logical_col is None:
                    i_logical_col = cp.cable.get_logical_number(col_name, RC.Col)
            if i_pin_row is None or i_pin_col is None or i_logical_row is None or i_logical_col is None or cp_row is None or cp_col is None:
                raise Exception('Bad code.')
            k = Key((op.center_xyu[0] * pitch, op.center_xyu[1] * pitch, np.deg2rad(op.angle)), orientation, switch_path,
                    img,  # type: ignore
                    code, i_pin_row, i_pin_col, i_logical_row, i_logical_col)
            keys_row[i_pin_row].append(k)
            keys_col[i_pin_col].append(k)

    def _orientation_to_angle_xy(orientation: FourOrientation):
        if orientation == FourOrientation.Left:
            return 0., ((min_xyu[0] - 1) * pitch, (min_xyu[1] + max_xyu[1]) * pitch / 2)
        elif orientation == FourOrientation.Back:
            return np.deg2rad(90.), ((min_xyu[0] + max_xyu[0]) * pitch / 2, (min_xyu[1] - 1) * pitch)
        elif orientation == FourOrientation.Right:
            return np.deg2rad(180.), ((max_xyu[0] + 1) * pitch, (min_xyu[1] + max_xyu[1]) * pitch / 2)
        else:
            return np.deg2rad(-90.), ((min_xyu[0] + max_xyu[0]) * pitch / 2, (max_xyu[1] + 1) * pitch)

    keys_rc: ty.Dict[RC, ty.Dict[int, ty.List[Key]]] = {RC.Row: keys_row, RC.Col: keys_col}
    route_rc: ty.Dict[RC, ty.Dict[int, Line]] = {RC.Col: {}, RC.Row: {}}
    entries_rc: ty.Dict[RC, ty.List[Entry]] = {}
    for rc in RC:
        entries = []
        for cp in cable_placements:
            angle, xy = _orientation_to_angle_xy(cp.orientation)
            entries += cp.cable.get_entries(angle, cp.flip, rc, xy)
        entries_rc[rc] = entries
        for i_entry, entry in enumerate(entries):
            if len(keys_rc[rc][i_entry]) == 0:
                continue
            dist_map = _make_dist_map(keys_rc[rc][i_entry], rc, entry)
            N = len(keys_rc[rc][i_entry])
            T = set(range(N))
            V: ty.Set[VertexType] = {(n, td) for n, td in product(range(N), TerminalDirection)}
            V_START = V | {START}
            GOAL: VertexType = (N, TerminalDirection.Left)
            V_GOAL = V | {GOAL}

            model = mip.Model()
            # binary variables indicating if arc (i,j) is used on the route or not
            x = {(i, j): model.add_var(var_type=mip.BINARY) for i, j in product(V_START, V_GOAL) if i[0] != j[0] and not (i == START and j == GOAL)}

            # continuous variable to prevent subtours: each terminal will have a
            # different sequential id in the planned route except the first one
            y = {n: model.add_var() for n in T}

            # objective function: minimize the distance
            model.objective = mip.minimize(mip.xsum(dist_map[i, j] * x[i, j] for i, j in product(V_START, V) if i[0] != j[0]))  # type: ignore

            # constraint: canont use the same direction of a terminal for enter / leave both
            for v in V:
                model += mip.xsum(x[v, j] for j in V_GOAL if j[0] != v[0]) + mip.xsum(x[i, v] for i in V_START if i[0] != v[0]) <= 1

            # constraint : leave each terminal only once except goal
            model += mip.xsum(x[START, j] for j in V) == 1
            for n in range(N):
                model += mip.xsum(x[(n, td), j] for td, j in product(TerminalDirection, V_GOAL) if n != j[0]) == 1

            # constraint : enter each terminal only once except start
            for m in range(N):
                model += mip.xsum(x[i, (m, td)] for td, i in product(TerminalDirection, V_START) if m != i[0]) == 1
            model += mip.xsum(x[i, GOAL] for i in V) == 1

            # subtour elimination
            for (n, m) in product(range(N), range(N)):
                if n != m:
                    model += y[n] - (N + 1) * mip.xsum(x[(n, td1), (m, td2)] for td1, td2 in product(TerminalDirection, TerminalDirection)) >= y[m] - N  # type: ignore

            # optimizing
            model.threads = 4
            model.optimize(max_seconds=5)  # type: ignore

            if model.num_solutions == 0:
                raise Exception('Bad code')
            line: Line = []
            i = START
            while True:
                js = [j for j in V_GOAL if (i, j) in x and x[i, j].x >= 0.99]  # type: ignore
                if len(js) == 0:
                    raise Exception('Bad code')
                j = js[0]
                if j == GOAL:
                    break
                line.append(j)
                i = (j[0], TerminalDirection.Left if j[1] == TerminalDirection.Right else TerminalDirection.Right)
            route_rc[rc][i_entry] = line

    return keys_rc, entries_rc, route_rc


def draw_wire(keys_rc: ty.Dict[RC, ty.Dict[int, ty.List[Key]]], entries_rc: ty.Dict[RC, ty.List[Entry]], route_rc: ty.Dict[RC, ty.Dict[int, Line]]):
    MAG = 200
    MARGIN = 200
    FONT_SIZE = 30
    xs: ty.Set[float] = set()
    ys: ty.Set[float] = set()
    wires_pn_rc: ty.Dict[RC, ty.Dict[int, ty.List[ty.Tuple[ty.List[ty.Tuple[float, float]], int]]]] = {RC.Col: {}, RC.Row: {}}
    for rc, eps in entries_rc.items():
        for i_entry, line in route_rc[rc].items():
            ep = eps[i_entry]
            orig_wire_path = (ep.x, ep.y, ep.angle)
            wires: ty.List[ty.Tuple[ty.List[ty.Tuple[float, float]], int]] = []
            for j in line:
                keys = keys_rc[rc][i_entry]
                dest_wire_path = _get_absolute_wire_path(keys[j[0]], rc, j[1], False)
                path_x, path_y, _, _, _ = dubins.dubins_path_planning(orig_wire_path[0], orig_wire_path[1], orig_wire_path[2], dest_wire_path[0], dest_wire_path[1], dest_wire_path[2], CURVATURE)
                wires.append(([(x, y) for x, y in zip(path_x, path_y)], j[0]))
                xs |= set(path_x)
                ys |= set(path_y)
                orig_wire_path = _get_absolute_wire_path(keys[j[0]], rc, TerminalDirection.Left if j[1] == TerminalDirection.Right else TerminalDirection.Right, True)
            wires.append(([(orig_wire_path[0], orig_wire_path[1])], -1))
            wires_pn_rc[rc][ep.pin_number] = wires
    size = np.array([max(xs) - min(xs), max(ys) - min(ys)])
    offset = np.array([min(xs), min(ys)])

    rainbow_cable_colors = [s for s in ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'grey', 'white']]
    font = ImageFont.truetype('verdana.ttf', FONT_SIZE)

    def _draw_selective(bold_rc: RC, rcs: ty.List[RC]):
        img = Image.new('RGB', (int(size[0] * MAG) + MARGIN * 2, int(size[1] * MAG) + MARGIN * 2), (255, ) * 3)
        keys: ty.List[Key] = []
        for ks in keys_rc[RC.Row].values():
            keys.extend(ks)
        for k in keys:
            k_img = k.img.rotate(np.rad2deg(_get_key_angle(k)), expand=True)  # type: ignore
            k_img_size = np.array(k_img.size)
            img.paste(k_img, tuple((np.array(k.key_location[:2] - offset) * MAG - k_img_size / 2 + MARGIN).astype(int)), mask=k_img)  # type: ignore
        draw = ImageDraw.Draw(img)
        for rc in rcs:
            for pn, wires in wires_pn_rc[rc].items():
                last_loc = None
                for wire in wires:
                    color = rainbow_cable_colors[pn % 10]
                    locs = (np.array(wire[0] - offset) * MAG).astype(int)
                    if last_loc is None:
                        pass
                    else:
                        draw.line((tuple(last_loc + MARGIN), tuple(locs[0] + MARGIN)), 'black', width=7)  # type: ignore
                        draw.line((tuple(last_loc + MARGIN), tuple(locs[0] + MARGIN)), color, width=3)  # type: ignore
                    last_loc = locs[-1]
                    if len(locs) > 1:
                        draw.line(tuple(tuple(i) for i in (locs + MARGIN).tolist()), 'black' if color == 'grey' else 'grey', width=int(WIRE_PITCH * MAG) if bold_rc == rc else 7, joint='curve')  # type: ignore
                        draw.line(tuple(tuple(i) for i in (locs + MARGIN).tolist()), color, width=int(WIRE_PITCH * MAG) - 8 if bold_rc == rc else 3, joint='curve')  # type: ignore
        img = ImageOps.mirror(img)
        img_w = img.size[0]
        draw = ImageDraw.Draw(img)
        for rc in rcs:
            last_pn = -1
            last_printed = False
            for pn, wires in wires_pn_rc[rc].items():
                if last_pn == pn - 1 and pn > 8 and ((pn % 5) != 0 or last_printed):
                    last_pn = pn
                    last_printed = False
                    continue
                last_pn = pn
                last_printed = True
                wire = wires[0]
                locs = (np.array(wire[0] - offset) * MAG).astype(int)
                legend_w, legend_h = draw.textsize(str(pn), font=font)
                x = wire[0][1][0] - wire[0][0][0]
                y = wire[0][1][1] - wire[0][0][1]
                if abs(x) > abs(y):
                    if x > 0.:
                        legend_offset = [0, -legend_h // 2]
                    else:
                        legend_offset = [-legend_w, -legend_h // 2]
                else:
                    if y > 0.:
                        legend_offset = [-legend_w // 2, -legend_h]
                    else:
                        legend_offset = [-legend_w // 2, 0]
                mirrored_xy = locs[0] + MARGIN
                draw.text((img_w - mirrored_xy[0] + legend_offset[0], mirrored_xy[1] + legend_offset[1]), str(pn), fill='black', font=font)
        return img

    return _draw_selective(RC.Row, [RC.Col, RC.Row]), _draw_selective(RC.Col, [RC.Row, RC.Col])


def generate_keymap(keys_rc: ty.Dict[RC, ty.Dict[int, ty.List[Key]]], n_logical_rc: ty.Dict[RC, int]):
    matrix_code: ty.Dict[int, ty.Dict[int, str]] = defaultdict(dict)
    keys: ty.List[Key] = []
    for ks in keys_rc[RC.Row].values():
        keys.extend(ks)
    for k in keys:
        matrix_code[k.i_logical_row][k.i_logical_col] = k.code
    code_str = ''
    for i_logical_row in range(n_logical_rc[RC.Row]):
        code_str += '        {'
        for i_logical_col in range(n_logical_rc[RC.Col]):
            if i_logical_row not in matrix_code or i_logical_col not in matrix_code[i_logical_row]:
                kc = 'KC_NO'
            elif matrix_code[i_logical_row][i_logical_col] is None:
                kc = 'KC_NO'
            else:
                kc = matrix_code[i_logical_row][i_logical_col]
            code_str += (kc + ', ')
        code_str += '},\n'
    return '''const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
    [0] = {
''' + code_str + '    }\n};\n'


@dataclass
class MainboardConstants:
    wire_names_rc: ty.Dict[RC, ty.List[str]]
    n_logical_rc: ty.Dict[RC, int]
    flat_cable_placements: ty.List[FlatCablePlacement]
    f3d_name: str


def get_mainboard_constants() -> MainboardConstants:
    mb = get_context().child[CN_INTERNAL].comp_attr[AN_MAINBOARD]
    mod = importlib.import_module(f'mainboard.{mb}')
    return mod.constants()


def get_cn_mainboard():
    return get_context().child[CN_INTERNAL].comp_attr[AN_MAINBOARD] + CNP_PARTS
