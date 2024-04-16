import typing as ty
from f360_common import BadCodeException, BadConditionException, get_context
from p2ppcb_composer.cmd_common import CommandHandlerBase
from p2ppcb_composer.cmd_init_project import InitializeP2ppcbProjectCommandHandler
from p2ppcb_composer.cmd_load_kle import LoadKleFileCommandHandler, ExtractKleFileCommandHandler
from p2ppcb_composer.cmd_info import InfoCommandHandler
from p2ppcb_composer.cmd_move_key import MoveKeyCommandHandler, SyncKeyCommandHandler
from p2ppcb_composer.cmd_change_key import ChangeKeyDescsCommandHandler, CheckKeyAssemblyCommandHandler
from p2ppcb_composer.cmd_matrix_route import AssignMatrixCommandHandler, GenerateRouteCommandHandler
from p2ppcb_composer.cmd_edit_frame import FillFrameCommandHandler, PlaceMainboardCommandHandler, PlaceFootCommandHandler, HolePartsCommandHandler, PlaceMiscCommandHandler
from p2ppcb_composer.cmd_set_attribute import SetAttributeCommandHandler
from p2ppcb_composer.cmd_remove_undercut import RemoveUndercutCommandHandler
from p2ppcb_composer.cmd_regex_selector import RegexSelectCommandHandler


TBT_ID_P2PPCB = 'p2ppcbToolbarTab'

PANEL_CLASSES: ty.List[ty.Tuple[str, str, ty.List[ty.Tuple[ty.Type, bool]]]] = [
    ('p2ppcbInitializeToolbarPanel', 'Initialize', [(InitializeP2ppcbProjectCommandHandler, True), (LoadKleFileCommandHandler, True), (ExtractKleFileCommandHandler, False), (InfoCommandHandler, False)]),
    ('p2ppcbEditKeyToolbarPanel', 'Edit Key', [(MoveKeyCommandHandler, True), (ChangeKeyDescsCommandHandler, True), (SyncKeyCommandHandler, True)]),
    ('p2ppcbMatrixToolbarPanel', 'Matrix', [(AssignMatrixCommandHandler, True), (GenerateRouteCommandHandler, True)]),
    ('p2ppcbFillHoleToolbarPanel', 'Fill/Hole', [(FillFrameCommandHandler, True), (HolePartsCommandHandler, True)]),
    ('p2ppcbPlacePartsToolbarPanel', 'Place Parts', [(PlaceMainboardCommandHandler, True), (PlaceFootCommandHandler, True), (PlaceMiscCommandHandler, False)]),
    ('p2ppcbCoverToolbarPanel', 'Cover', [(RegexSelectCommandHandler, True), (RemoveUndercutCommandHandler, True)]),
    ('p2ppcbPartsEditToolbarPanel', 'Parts Edit', [(SetAttributeCommandHandler, True), (CheckKeyAssemblyCommandHandler, True)]),
]

HANDLERS = []


def get_cmd_id(handler_class: ty.Type):
    return handler_class.__name__ + 'ButtonId'


def get_cmd_def(handler_class: ty.Type):
    cmd_id = get_cmd_id(handler_class)
    handler: CommandHandlerBase = handler_class()
    con = get_context()
    cmd_defs = con.ui.commandDefinitions
    cmd_def = cmd_defs.itemById(cmd_id)
    if cmd_def is not None:
        cmd_def.deleteMe()
        cmd_def = cmd_defs.itemById(cmd_id)
        if cmd_def is not None:
            raise BadCodeException(f'{cmd_id} deleteMe() failed.')
    cmd_def = cmd_defs.addButtonDefinition(cmd_id, handler.cmd_name, handler.tooltip, handler.resource_folder)
    cmd_def.commandCreated.add(handler)
    HANDLERS.append(handler)
    return cmd_def


def init_toolbar():
    con = get_context()
    if not con.ui.isTabbedToolbarUI:
        raise BadConditionException('Classic UI is not supported.')

    design_workspace = con.ui.workspaces.itemById('FusionSolidEnvironment')
    if design_workspace is None:
        raise BadConditionException('FusionSolidEnvironment not found in workspaces.')
    tabs = design_workspace.toolbarTabs
    tab = tabs.itemById(TBT_ID_P2PPCB)
    if tab is None:
        tab = tabs.add(TBT_ID_P2PPCB, 'P2PPCB')
    panels = tab.toolbarPanels

    for panel_id, panel_name, handler_classes in PANEL_CLASSES:
        panel = panels.itemById(panel_id)
        if panel is None:
            panel = panels.add(panel_id, panel_name)
        for handler_class, promote in handler_classes:
            panel_ctrl_id = get_cmd_id(handler_class)
            panel_ctrl = panel.controls.itemById(panel_ctrl_id)
            if panel_ctrl is not None:
                panel_ctrl.deleteMe()
                panel_ctrl = panel.controls.itemById(panel_ctrl_id)
                if panel_ctrl is not None:
                    raise BadCodeException(f'{panel_ctrl_id} deleteMe() failed.')
            panel_ctrl = panel.controls.addCommand(get_cmd_def(handler_class))
            panel_ctrl.isPromotedByDefault = promote


def terminate_toolbar():
    con = get_context()

    cmd_defs = con.ui.commandDefinitions
    design_workspace = con.ui.workspaces.itemById('FusionSolidEnvironment')
    if design_workspace is None:
        return

    tabs = design_workspace.toolbarTabs
    tab = tabs.itemById(TBT_ID_P2PPCB)
    if tab is None:
        return
    panels = tab.toolbarPanels
    for panel_id, _, handler_classes in PANEL_CLASSES:
        panel = panels.itemById(panel_id)
        if panel is None:
            continue
        for ctrl in list(panel.controls):
            ctrl.deleteMe()
        if len(panel.controls) > 0:
            print(f'{panel_id} controls deleteMe() failed.')
        panel.deleteMe()
        if panels.itemById(panel_id) is not None:
            print(f'{panel_id} deleteMe() failed.')
            continue
        for handler_class, _ in handler_classes:
            cmd_id = get_cmd_id(handler_class)
            cmd_def = cmd_defs.itemById(cmd_id)
            if cmd_def is not None:
                cmd_def.deleteMe()
                if cmd_defs.itemById(cmd_id) is not None:
                    print(f'{cmd_id} deleteMe() failed.')
    tab.deleteMe()
    if tabs.itemById(TBT_ID_P2PPCB) is not None:
        print(f'{TBT_ID_P2PPCB} deleteMe() failed.')

    HANDLERS.clear()
