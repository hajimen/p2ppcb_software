import base64
import importlib
import json5
import json
from operator import attrgetter
import re
from itertools import product
from collections import defaultdict
from enum import Enum, IntEnum, auto
from dataclasses import dataclass, field
import typing as ty
import zlib

import mip
from PIL import Image, ImageDraw, ImageOps, ImageFont
from PIL.Image import Image as ImageType
import numpy as np
from p2ppcb_composer.cmd_common import AN_MAINBOARD
from route import dubins
from f360_common import AN_ROW_NAME, AN_SWITCH_DESC, AN_SWITCH_ORIENTATION, CN_INTERNAL, CN_KEY_LOCATORS, CNP_PARTS, BadCodeException, \
    get_context, key_locator_name, load_kle_by_b64, get_part_info, get_parts_data_path, AN_KEY_PITCH_W, AN_KEY_PITCH_D, FourOrientation, AN_KLE_B64, \
    CURRENT_DIR, BadConditionException
from p2ppcb_parts_resolver.resolver import SPN_SWITCH_ANGLE


I_CODE0_LABEL = 9
N_CODES = 3
N_QMK_LAYER = 4  # VIA supports 4 layers max.
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


RC_CP = ty.Tuple[RC, int]
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
    switch_angle: float
    path: SwitchPath
    img: ImageType = field(compare=False)
    codes: ty.List[str]
    i_row: int
    i_col: int
    i_logical_row: int
    i_logical_col: int
    i_kle: int


KeysOnPinType = ty.Dict[ty.Tuple[int, int], ty.List[Key]]


@dataclass
class WireGroup:
    start: int
    end: int
    logical_start: int
    rc: RC
    led: bool
    wire_name_start: int


def _get_rot(angle):
    return np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])


class FlatCable:
    WIRE_NAME_N_RE = re.compile(r'.+?(\d+)$')

    def __init__(self, n_wire: int, first_index_in_wire_name: int, wire_pitch: float) -> None:
        self.n_wire = n_wire
        self.groups: ty.List[WireGroup] = []
        self.first_index_in_wire_name = first_index_in_wire_name
        self.wire_pitch = wire_pitch

    def add_group(self, wire_group: WireGroup):
        self.groups.append(wire_group)

    def get_entries(self, angle: float, start_xy: ty.Tuple[float, float], center_xy: ty.Tuple[float, float], rc: RC, flip: bool):
        pos = []
        nps = []
        nls = []
        for g in self.groups:
            if g.rc == rc:
                for i in range(g.start, g.end):
                    pos.append((i * self.wire_pitch, 0.))
                    nps.append(i)
                    nls.append(g.logical_start + i - g.start)
        pos = np.array(pos)
        entries: ty.Dict[int, Entry] = defaultdict()
        rot = _get_rot(angle)
        start = np.array(start_xy)
        entry_angle = angle + (-np.pi / 2 if flip else np.pi / 2)
        for p, pn, ln in zip(pos, nps, nls):
            rp = (p @ rot) + start
            rp = np.array([rp[0], -rp[1]]) + np.array(center_xy)
            entries[pn] = Entry(rp[0], rp[1], entry_angle, pn, ln)
        return entries

    def _get_group(self, wire_name: str, rc: RC):
        led = 'LED' in wire_name
        m = FlatCable.WIRE_NAME_N_RE.match(wire_name)
        if m is None:
            raise BadCodeException(f"wire_name: {wire_name} lacks number.")
        i_in_name = int(m.group(1)) - self.first_index_in_wire_name
        for g in self.groups:
            if g.rc == rc and g.led == led:
                i_in_group = i_in_name - g.wire_name_start
                if i_in_group >= 0 and i_in_group < g.end - g.start:
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
    start: ty.Tuple[float, float]
    angle: float
    cable: FlatCable
    flip: bool


def _get_key_angle(k: Key):
    return k.key_location[2] + k.switch_angle


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
    try:
        import mip.cbc
    except NameError:
        raise BadConditionException('Currently PC0 cannot generate route on Apple Silicon. Dig "arch" command to run F360 by x86_64.')
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
    pitch_w = float(inl_occ.comp_attr[AN_KEY_PITCH_W])
    pitch_d = float(inl_occ.comp_attr[AN_KEY_PITCH_D])
    keys_row: KeysOnPinType = defaultdict(list)
    keys_col: KeysOnPinType = defaultdict(list)
    image_cache = {}
    for pattern_name, specs_ops in specs_ops_on_pn.items():
        for i, (specifier, op) in enumerate(specs_ops):
            if op is None:
                raise BadCodeException()
            kl_name = key_locator_name(i, pattern_name)
            kl_occ = locators_occ.child[kl_name]
            switch_desc = kl_occ.comp_attr[AN_SWITCH_DESC]
            codes = op.legend[I_CODE0_LABEL:I_CODE0_LABEL + N_CODES]
            if kl_occ.comp_attr[AN_ROW_NAME].startswith('LED'):
                specifier += ' LED'
            filename, wiring_parameters = pi.resolve_pcb_wiring(specifier, switch_desc)
            switch_orientation = FourOrientation[kl_occ.comp_attr[AN_SWITCH_ORIENTATION]]
            wp = {k: v.m_as('rad') if k.endswith('Angle') else v.m_as('cm') for k, v in wiring_parameters.items()}
            switch_angle = ROT_RAD[switch_orientation] + wp[SPN_SWITCH_ANGLE]
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
            i_pin_col = None
            i_logical_col = None
            i_cp_row = -1
            i_cp_col = -1
            for i, cp in enumerate(cable_placements):
                if i_pin_row is None:
                    i_pin_row = cp.cable.get_pin_number(row_name, RC.Row)
                    i_cp_row = i
                if i_logical_row is None:
                    i_logical_row = cp.cable.get_logical_number(row_name, RC.Row)
                if i_pin_col is None:
                    i_pin_col = cp.cable.get_pin_number(col_name, RC.Col)
                    i_cp_col = i
                if i_logical_col is None:
                    i_logical_col = cp.cable.get_logical_number(col_name, RC.Col)
            if i_pin_row is None or i_pin_col is None or i_logical_row is None or i_logical_col is None or i_cp_row == -1 or i_cp_col == -1:
                raise BadCodeException()
            k = Key((op.center_xyu[0] * pitch_w, op.center_xyu[1] * pitch_d, np.deg2rad(-op.angle)), switch_angle, switch_path,
                    img,  # type: ignore
                    codes, i_pin_row, i_pin_col, i_logical_row, i_logical_col, op.i_kle)
            keys_row[i_cp_row, i_pin_row].append(k)
            keys_col[i_cp_col, i_pin_col].append(k)

    keys_rc: ty.Dict[RC, KeysOnPinType] = {RC.Row: keys_row, RC.Col: keys_col}
    route_rccp: ty.Dict[RC_CP, ty.Dict[int, Line]] = defaultdict(dict)
    entries_rccp: ty.Dict[RC_CP, ty.Dict[int, Entry]] = {}
    center_xy = ((min_xyu[0] + max_xyu[0]) * pitch_w / 2, (min_xyu[1] + max_xyu[1]) * pitch_d / 2)
    for rc, (i_cp, cp) in product(RC, enumerate(cable_placements)):
        entries = cp.cable.get_entries(cp.angle, cp.start, center_xy, rc, cp.flip)
        if len(entries) == 0:
            continue
        entries_rccp[rc, i_cp] = entries
        for i_pin, entry in entries.items():
            keys = keys_rc[rc][(i_cp, i_pin)]
            if len(keys) == 0:
                continue
            dist_map = _make_dist_map(keys, rc, entry)
            N = len(keys)
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

            # constraint: cannot use the same direction of a terminal for enter / leave both
            for v in V:
                model += mip.xsum(x[v, j] for j in V_GOAL if j[0] != v[0]) + mip.xsum(x[i, v] for i in V_START if i[0] != v[0]) <= 1  # type: ignore

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
                raise BadCodeException()
            line: Line = []
            i = START
            while True:
                js = [j for j in V_GOAL if (i, j) in x and x[i, j].x >= 0.99]  # type: ignore
                if len(js) == 0:
                    raise BadCodeException()
                j = js[0]
                if j == GOAL:
                    break
                line.append(j)
                i = (j[0], TerminalDirection.Left if j[1] == TerminalDirection.Right else TerminalDirection.Right)
            route_rccp[rc, i_cp][i_pin] = line

    return keys_rc, entries_rccp, route_rccp


def draw_wire(keys_rc: ty.Dict[RC, KeysOnPinType], entries_rccp: ty.Dict[RC_CP, ty.Dict[int, Entry]], route_rccp: ty.Dict[RC_CP, ty.Dict[int, Line]], cable_placements: ty.List[FlatCablePlacement]):
    MAG = 200
    MARGIN = 200
    FONT_SIZE = 30
    WIRE_TABLE_ROW = 400
    WIRE_TABLE_PITCH = 100
    WIRE_TABLE_MARGIN = 100
    xs: ty.Set[float] = set()
    ys: ty.Set[float] = set()
    wires_pn_rc: ty.Dict[RC, ty.Dict[int, ty.List[ty.Tuple[ty.List[ty.Tuple[float, float]], int]]]] = {RC.Col: {}, RC.Row: {}}
    for (rc, i_cp), entries in entries_rccp.items():
        if len(entries) == 0:
            continue
        for i_pin, line in route_rccp[rc, i_cp].items():
            ep = entries[i_pin]
            orig_wire_path = (ep.x, ep.y, ep.angle)
            wires: ty.List[ty.Tuple[ty.List[ty.Tuple[float, float]], int]] = []
            for j in line:
                keys = keys_rc[rc][i_cp, i_pin]
                dest_wire_path = _get_absolute_wire_path(keys[j[0]], rc, j[1], False)
                path_x, path_y, _, _, _ = dubins.dubins_path_planning(orig_wire_path[0], orig_wire_path[1], orig_wire_path[2], dest_wire_path[0], dest_wire_path[1], dest_wire_path[2], CURVATURE)
                wires.append(([(x, y) for x, y in zip(path_x, path_y)], j[0]))
                xs |= set(path_x)
                ys |= set(path_y)
                orig_wire_path = _get_absolute_wire_path(keys[j[0]], rc, TerminalDirection.Left if j[1] == TerminalDirection.Right else TerminalDirection.Right, True)
            wires.append(([(orig_wire_path[0], orig_wire_path[1])], -1))
            wires_pn_rc[rc][ep.pin_number] = wires
    size = np.array([max(xs) - min(xs) + 1, max(ys) - min(ys) + 1])
    offset = np.array([min(xs), min(ys)])

    rainbow_cable_colors = [s for s in ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'grey', 'white']]
    font = ImageFont.truetype(str(CURRENT_DIR / 'font/UbuntuMono-R.ttf'), FONT_SIZE)
    wire_pitch_pnrc: ty.Dict[ty.Tuple[int, RC], float] = {}
    i_cp_pnrc: ty.Dict[ty.Tuple[int, RC], int] = {}
    for (rc, i_cp), entries in entries_rccp.items():
        if len(entries) == 0:
            continue
        cp = cable_placements[i_cp]
        for i_pin, _ in route_rccp[rc, i_cp].items():
            pn = entries[i_pin].pin_number
            wire_pitch_pnrc[pn, rc] = cp.cable.wire_pitch
            i_cp_pnrc[pn, rc] = i_cp
    wire_table_height = WIRE_TABLE_ROW * (max([i_cp for (_, i_cp), entries in entries_rccp.items() if len(entries) > 0]) + 1)
    wire_table_width = WIRE_TABLE_PITCH * (max([
        max([en.pin_number for en in entries.values()])
        for entries in entries_rccp.values()
    ]) + 1) + MARGIN * 2

    def _width(pn, rc, bold_rc):
        return int(wire_pitch_pnrc[pn, rc] * MAG) - 8 if bold_rc == rc else 3, int(wire_pitch_pnrc[pn, rc] * MAG) if bold_rc == rc else 7

    def _draw_selective(bold_rc: RC, rcs: ty.List[RC]):
        img_wt = Image.new('RGB', (wire_table_width, wire_table_height), (255, ) * 3)  # type: ignore
        draw_wt = ImageDraw.Draw(img_wt)
        for (rc, i_cp), entries in entries_rccp.items():
            if len(entries) == 0:
                continue
            cp = cable_placements[i_cp]
            for i_pin, _ in route_rccp[rc, i_cp].items():
                pn = entries[i_pin].pin_number
                wt_y = i_cp_pnrc[pn, rc] * WIRE_TABLE_ROW
                color = rainbow_cable_colors[(pn + 1) % 10]  # Wire number always starts from 1.
                border_color = 'black' if color == 'grey' else 'grey'
                width, border_width = _width(pn, rc, bold_rc)
                draw_wt.line(
                    (
                        (WIRE_TABLE_MARGIN + WIRE_TABLE_PITCH * pn, wt_y + WIRE_TABLE_MARGIN + FONT_SIZE + 7),
                        (WIRE_TABLE_MARGIN + WIRE_TABLE_PITCH * pn, wt_y + WIRE_TABLE_ROW - WIRE_TABLE_MARGIN - FONT_SIZE - 7)),
                    border_color, width=border_width)  # type: ignore
                draw_wt.line(
                    (
                        (WIRE_TABLE_MARGIN + WIRE_TABLE_PITCH * pn, wt_y + WIRE_TABLE_MARGIN + FONT_SIZE + 7),
                        (WIRE_TABLE_MARGIN + WIRE_TABLE_PITCH * pn, wt_y + WIRE_TABLE_ROW - WIRE_TABLE_MARGIN - FONT_SIZE - 7)),
                    color, width=width)  # type: ignore
                draw_wt.text(
                    (WIRE_TABLE_MARGIN + WIRE_TABLE_PITCH * pn, wt_y + WIRE_TABLE_MARGIN),
                    str(pn + 1),
                    fill='black', font=font, anchor='mt', stroke_width=2, stroke_fill='white'
                )
                for wn in get_mainboard_constants().wire_names_rc[rc]:
                    if cp.cable.get_pin_number(wn, rc) == pn:
                        draw_wt.text(
                            (WIRE_TABLE_MARGIN + WIRE_TABLE_PITCH * pn, wt_y + WIRE_TABLE_ROW - WIRE_TABLE_MARGIN - FONT_SIZE),
                            str(wn),
                            fill='black', font=font, anchor='mt', stroke_width=2, stroke_fill='white'
                        )
                        break
        img_wt = img_wt.crop(ImageOps.invert(img_wt).getbbox())

        img = Image.new('RGB', (int(size[0] * MAG) + MARGIN * 2, int(size[1] * MAG) + MARGIN * 2), (255, ) * 3)  # type: ignore
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
                color = rainbow_cable_colors[(pn + 1) % 10]
                border_color = 'black' if color == 'grey' else 'grey'
                for wire in wires:
                    locs = (np.array(wire[0] - offset) * MAG).astype(int)
                    if last_loc is None:
                        pass
                    else:
                        draw.line((tuple(last_loc + MARGIN), tuple(locs[0] + MARGIN)), 'black', width=7)  # type: ignore
                        draw.line((tuple(last_loc + MARGIN), tuple(locs[0] + MARGIN)), color, width=3)  # type: ignore
                    last_loc = locs[-1]
                    if len(locs) > 1:
                        width, border_width = _width(pn, rc, bold_rc)
                        draw.line(tuple(tuple(i) for i in (locs + MARGIN).tolist()), border_color, width=border_width, joint='curve')  # type: ignore
                        draw.line(tuple(tuple(i) for i in (locs + MARGIN).tolist()), color, width=width, joint='curve')  # type: ignore
        img = ImageOps.mirror(img)
        img_w = img.size[0]
        draw = ImageDraw.Draw(img)
        for rc in rcs:
            last_pn = -1
            last_printed = False
            for pn, wires in wires_pn_rc[rc].items():
                pn1 = pn + 1  # Wire number always starts from 1.
                if last_pn == pn1 - 1 and pn1 > 8 and ((pn1 % 5) != 0 or last_printed):
                    last_pn = pn1
                    last_printed = False
                    continue
                last_pn = pn1
                last_printed = True
                wire = wires[0]
                locs = (np.array(wire[0] - offset) * MAG).astype(int)
                bbox = draw.textbbox((0, 0), str(pn1), font=font)
                legend_w = int(bbox[2] - bbox[0])
                legend_h = int(bbox[3] - bbox[1])
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
                draw.multiline_text((img_w - mirrored_xy[0] + legend_offset[0], mirrored_xy[1] + legend_offset[1]), str(pn1), fill='black', font=font,
                                    stroke_width=2, stroke_fill='white')
        img = img.crop(ImageOps.invert(img).getbbox())
        ret = Image.new('RGB', (max([img.size[0], img_wt.size[0]]), img.size[1] + img_wt.size[1] + WIRE_TABLE_MARGIN), (255, ) * 3)  # type: ignore
        ret.paste(img, (0, 0))
        ret.paste(img_wt, (0, img.size[1] + WIRE_TABLE_MARGIN))
        return ret

    return _draw_selective(RC.Row, [RC.Col, RC.Row]), _draw_selective(RC.Col, [RC.Row, RC.Col])


def read_json_by_b64(json_b64: str) -> ty.Any:
    content = zlib.decompress(base64.b64decode(json_b64))
    return json5.loads(content)


def generate_keymap(keys_rc: ty.Dict[RC, KeysOnPinType], mbc: 'MainboardConstants'):
    con = get_context()
    matrix_code: ty.Dict[int, ty.Dict[int, ty.List[str]]] = defaultdict(dict)
    keys: ty.List[Key] = []
    for ks in keys_rc[RC.Row].values():
        keys.extend(ks)
    keys = sorted(keys, key=attrgetter('i_kle'))
    for k in keys:
        matrix_code[k.i_logical_row][k.i_logical_col] = k.codes

    kle_json = []
    i_kle = 0
    for r in read_json_by_b64(con.child[CN_INTERNAL].comp_attr[AN_KLE_B64]):
        nr = []
        for e in r:
            if isinstance(e, str):
                k = keys[i_kle]
                nr.append(f'{k.i_logical_row},{k.i_logical_col}')
                i_kle += 1
            elif isinstance(e, dict):
                ne = {}
                for k in ['x', 'x2', 'y', 'y2', 'rx', 'ry', 'w', 'w2', 'h', 'h2', 'r']:
                    if k in e:
                        ne[k] = e[k]
                nr.append(ne)
            else:
                nr.append(e)
        kle_json.append(nr)
    mbc = get_mainboard_constants()
    via_dic = {
        'name': con.des.parentDocument.name,
        'vendorId': 'FEED',  # https://github.com/tmk/tmk_keyboard/issues/150
        'productId': mbc.product_id,
        'matrix': {
            'rows': mbc.n_logical_rc[RC.Row], 'cols': mbc.n_logical_rc[RC.Col]
        },
        'layouts': {
            'keymap': kle_json
        }
    }
    
    qmk_str = ''
    for i_layer in range(N_QMK_LAYER):
        qmk_str += '    [' + str(i_layer) + '] = {\n'
        for i_logical_row in range(mbc.n_logical_rc[RC.Row]):
            qmk_str += '        {'
            for i_logical_col in range(mbc.n_logical_rc[RC.Col]):
                if i_logical_row not in matrix_code or i_logical_col not in matrix_code[i_logical_row]:
                    kc = 'KC_NO'
                elif matrix_code[i_logical_row][i_logical_col] is None:
                    kc = 'KC_NO'
                elif len(matrix_code[i_logical_row][i_logical_col]) <= i_layer:
                    kc = 'KC_NO'
                else:
                    c = matrix_code[i_logical_row][i_logical_col][i_layer]
                    kc = 'KC_NO' if c is None else c
                qmk_str += (kc + ', ')
            qmk_str += '},\n'
        qmk_str += '    },\n'
    return 'const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {\n' + qmk_str + '};\n', json.dumps(via_dic, indent=2)


@dataclass
class MainboardConstants:
    wire_names_rc: ty.Dict[RC, ty.List[str]]
    n_logical_rc: ty.Dict[RC, int]
    flat_cables: ty.List[FlatCable]
    f3d_name: str
    product_id: str


def get_mainboard_constants() -> MainboardConstants:
    mb = get_context().child[CN_INTERNAL].comp_attr[AN_MAINBOARD]
    mod = importlib.import_module(f'mainboard.{mb}')
    return mod.constants()


def get_cn_mainboard():
    return get_context().child[CN_INTERNAL].comp_attr[AN_MAINBOARD] + CNP_PARTS
