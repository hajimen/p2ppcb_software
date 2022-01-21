from route.route import RC, FlatCable, WireGroup, MainboardConstants

WIRE_NAMES_RC = {
    RC.Row: [f'S{i}' for i in range(16)],
    RC.Col: [f'D{i}' for i in range(12)]
}
N_LOGICAL_RC = {RC.Row: 16, RC.Col: 12}

CABLE = FlatCable(30, 0)
CABLE.add_group(WireGroup(0, 8, 0, RC.Row, False))
CABLE.add_group(WireGroup(8, 20, 0, RC.Col, False))
CABLE.add_group(WireGroup(22, 30, 8, RC.Row, False))
CONSTANTS = MainboardConstants(WIRE_NAMES_RC, N_LOGICAL_RC, [CABLE], 'Bob.f3d')


def constants():
    return CONSTANTS
