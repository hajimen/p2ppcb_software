from route.route import RC, FlatCable, WireGroup, MainboardConstants

WIRE_NAMES_RC = {
    RC.Row: [f'S{i}' for i in range(16)] + ['LED_S0', 'LED_S1'],
    RC.Col: [f'D{i}' for i in range(12)] + [f'LED_D{i}' for i in range(3)]
}
N_LOGICAL_RC = {RC.Row: 18, RC.Col: 12}
WIRE_PITCH = 0.1

CABLE = FlatCable(30, 0, WIRE_PITCH)
CABLE.add_group(WireGroup(0, 8, 0, RC.Row, False))
CABLE.add_group(WireGroup(8, 20, 0, RC.Col, False))
CABLE.add_group(WireGroup(22, 24, 16, RC.Row, True))
CABLE.add_group(WireGroup(24, 27, 0, RC.Col, True))
CABLE.add_group(WireGroup(28, 36, 8, RC.Row, False))
CONSTANTS = MainboardConstants(WIRE_NAMES_RC, N_LOGICAL_RC, [CABLE], 'Charlotte.f3d', '0x9605')


def constants():
    return CONSTANTS
