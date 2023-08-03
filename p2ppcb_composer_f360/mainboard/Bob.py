from route.route import RC, FlatCable, WireGroup, MainboardConstants

WIRE_NAMES_RC = {
    RC.Row: [f'S{i}' for i in range(16)],
    RC.Col: [f'D{i}' for i in range(12)]
}
N_LOGICAL_RC = {RC.Row: 16, RC.Col: 12}
WIRE_PITCH = 0.1

CABLE = FlatCable(30, 0, WIRE_PITCH)
CABLE.add_group(WireGroup(0, 8, 0, RC.Row, False, 0))
CABLE.add_group(WireGroup(8, 20, 0, RC.Col, False, 0))
CABLE.add_group(WireGroup(22, 30, 8, RC.Row, False, 8))
CONSTANTS = MainboardConstants(WIRE_NAMES_RC, N_LOGICAL_RC, [CABLE], 'Bob.f3d', '0xde26')


def constants():
    return CONSTANTS
