from route.route import RC, FlatCable, WireGroup, MainboardConstants

WIRE_NAMES_RC = {
    RC.Row: [f'ROW_{i + 1}' for i in range(8)] + ['LED_ROW_1', 'LED_ROW_2'],
    RC.Col: [f'COL_{i + 1}' for i in range(24)] + [f'LED_COL_{i + 1}' for i in range(6)]
}
N_LOGICAL_RC = {RC.Row: 10, RC.Col: 24}
WIRE_PITCH = 0.127

ROW_CABLE = FlatCable(10, 1, WIRE_PITCH)
ROW_CABLE.add_group(WireGroup(0, 8, 0, RC.Row, False))
ROW_CABLE.add_group(WireGroup(8, 10, 8, RC.Row, True))
COL_CABLE = FlatCable(30, 1, WIRE_PITCH)
COL_CABLE.add_group(WireGroup(0, 24, 0, RC.Col, False))
COL_CABLE.add_group(WireGroup(24, 30, 0, RC.Col, True))
CONSTANTS = MainboardConstants(WIRE_NAMES_RC, N_LOGICAL_RC, [ROW_CABLE, COL_CABLE], 'Alice.f3d', '0x7970')


def constants():
    return CONSTANTS
