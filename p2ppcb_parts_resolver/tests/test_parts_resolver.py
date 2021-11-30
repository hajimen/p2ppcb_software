import typing as ty
import pathlib
import sys
import unittest

CURRENT_DIR = pathlib.Path(__file__).parent.parent
PARTS_DATA_DIR = CURRENT_DIR.parent / 'p2ppcb_parts_data_f360'

if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))
ap = CURRENT_DIR / 'app-packages'
if str(ap) not in sys.path:
    sys.path.append(str(ap))
del ap

import numpy as np
import p2ppcb_parts_resolver.resolver as parts_resolver
from PIL import Image, ImageChops


class TestPartsResolver(unittest.TestCase):
    def render_total_image(self, specs_ops_on_pn: ty.Dict[str, ty.List[ty.Tuple[str, parts_resolver.OccurrenceParameter]]], min_xyu, max_xyu):
        U = 216
        min_xyu = np.array(min_xyu)
        max_xyu = np.array(max_xyu)
        w, h = ((max_xyu - min_xyu) * U).astype(int)
        canvas = Image.new('RGBA', (w, h), color=(0, 0, 0, 255))
        for pn, specs_ops in specs_ops_on_pn.items():
            for specifier, op in specs_ops:
                img = Image.open(op.image_file_path)
                m = int(max(img.size) * 1.5) + 1
                pi = Image.new('RGBA', (m, m), color=(0, 0, 0, 0))
                pi.paste(img, box=((m - img.size[0]) // 2, (m - img.size[1]) // 2))
                pi = pi.rotate(-op.angle)
                r = op.angle * np.pi / 180
                rot_mat = np.array([[np.cos(r), - np.sin(r)], [np.sin(r), np.cos(r)]])
                center_x, center_y = (np.array(op.center_xyu) + rot_mat @ np.array(op.image_center_offset_u) - min_xyu) * U
                canvas.paste(pi, box=(int(center_x) - m // 2, int(center_y) - m // 2), mask=pi)
        return canvas

    def test_resolve_kle(self):
        fns = ['60percent', 'single', 'iso105', 'ergodox', 'single-rotated-iso', 'single-bigass', 'rotation', 'stepped']
        pi = parts_resolver.PartsInfo(PARTS_DATA_DIR / parts_resolver.PARTS_INFO_DIRNAME)
        for fn in fns:
            canvas = self.render_total_image(*pi.resolve_kle(pathlib.Path(f'test_data/kle/{fn}.json'), pathlib.Path('tmp')))
            oracle = Image.open(f'test_data/kle/{fn}.png')
            self.assertIsNone(ImageChops.difference(canvas, oracle).getbbox(), f'{fn} failed.')

    def test_resolve_specifier(self):
        pi = parts_resolver.PartsInfo(PARTS_DATA_DIR / parts_resolver.PARTS_INFO_DIRNAME)
        specs_ops_on_pn, min_xyu, max_xyu = pi.resolve_kle(CURRENT_DIR / 'test_data/kle/oem_set.json', CURRENT_DIR / 'tmp')
        for pn, specs_ops in specs_ops_on_pn.items():
            for specifier, _ in specs_ops:
                result = pi.resolve_specifier(specifier, 'OEM profile', 'Cherry-style plate mount', 'Choc V2', parts_resolver.AlignTo.TravelBottom)
                if result is None:
                    raise Exception(f'The part is not available. specifier: {specifier}')
        # part_filename, part_parameters, part_placeholder, part_z_pos = pi.resolve_specifier('Homing 1u', 'DSA', 'Cherry-style plate mount', 'Choc V2', parts_resolver.AlignTo.TravelBottom)
        # decal_parameters = pi.resolve_decal('Homing 1u', 'Key Locator')
        pass

    def test_resolve_wiring(self):
        pi = parts_resolver.PartsInfo(PARTS_DATA_DIR / parts_resolver.PARTS_INFO_DIRNAME)
        filename, params = pi.resolve_pcb_wiring('1u', 'Choc V2')
        filename, params = pi.resolve_pcb_wiring('1u LED', 'Choc V2')

    def test_dsa_iso(self):
        pi = parts_resolver.PartsInfo(PARTS_DATA_DIR / parts_resolver.PARTS_INFO_DIRNAME)
        specs_ops_on_pn, min_xyu, max_xyu = pi.resolve_kle(CURRENT_DIR / 'test_data/kle/dsa-iso.json', CURRENT_DIR / 'tmp')
        for pn, specs_ops in specs_ops_on_pn.items():
            for specifier, _ in specs_ops:
                result = pi.resolve_specifier(specifier, 'DSA', 'Cherry-style plate mount', 'Choc V2', parts_resolver.AlignTo.TravelBottom)
                if result is None:
                    raise Exception(f'The part is not available. specifier: {specifier}')

    def test_dsa_small(self):
        pi = parts_resolver.PartsInfo(PARTS_DATA_DIR / parts_resolver.PARTS_INFO_DIRNAME)
        specs_ops_on_pn, min_xyu, max_xyu = pi.resolve_kle(CURRENT_DIR / 'test_data/kle/dsa_small.json', CURRENT_DIR / 'tmp')
        for pn, specs_ops in specs_ops_on_pn.items():
            for specifier, _ in specs_ops:
                result = pi.resolve_specifier(specifier, 'DSA', 'Cherry-style plate mount', 'Choc V2', parts_resolver.AlignTo.TravelBottom)
                if result is None:
                    raise Exception(f'The part is not available. specifier: {specifier}')
