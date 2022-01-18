from f360_common import FourOrientation
from route.route import RC, FlatCable, WireGroup, FlatCablePlacement, MainboardConstants

WIRE_NAMES_RC = {
    RC.Row: [f'ROW_{i + 1}' for i in range(8)] + ['LED_ROW_1', 'LED_ROW_2'],
    RC.Col: [f'COL_{i + 1}' for i in range(24)] + [f'LED_COL_{i + 1}' for i in range(6)]
}
N_LOGICAL_RC = {RC.Row: 10, RC.Col: 24}

ROW_CABLE = FlatCable(10, 1)
ROW_CABLE.add_group(WireGroup(0, 8, 0, RC.Row, False))
ROW_CABLE.add_group(WireGroup(8, 10, 8, RC.Row, True))
COL_CABLE = FlatCable(30, 1)
COL_CABLE.add_group(WireGroup(0, 24, 0, RC.Col, False))
COL_CABLE.add_group(WireGroup(24, 30, 0, RC.Col, True))
ROW_PLACEMENT = FlatCablePlacement(True, FourOrientation.Right, ROW_CABLE)
COL_PLACEMENT = FlatCablePlacement(False, FourOrientation.Back, COL_CABLE)
CONSTANTS = MainboardConstants(WIRE_NAMES_RC, N_LOGICAL_RC, [ROW_PLACEMENT, COL_PLACEMENT], 'Alice.f3d')


def constants():
    return CONSTANTS
