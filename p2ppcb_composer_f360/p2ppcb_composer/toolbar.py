import typing as ty
import sys
from f360_common import BadCodeException, BadConditionException, get_context, SEPARATE_PYTHON_CONFIG_PATH, set_separate_python, CURRENT_DIR
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

    if sys.platform == 'darwin':
        import p2ppcb_parts_resolver.resolver as parts_resolver
        if SEPARATE_PYTHON_CONFIG_PATH.is_file():
            with open(SEPARATE_PYTHON_CONFIG_PATH, 'r') as f:
                p = f.readlines()
            if len(p) > 0:
                p = p[0].strip()
                try:
                    parts_resolver.PartsInfo(CURRENT_DIR.parent / 'p2ppcb_parts_data_f360' / parts_resolver.PARTS_INFO_DIRNAME, p)
                    set_separate_python(p)
                except Exception:
                    SEPARATE_PYTHON_CONFIG_PATH.unlink()
            else:
                SEPARATE_PYTHON_CONFIG_PATH.unlink()
        if not SEPARATE_PYTHON_CONFIG_PATH.is_file():
            p = config_separate_python()
            if p is None:
                return
            try:
                pi = parts_resolver.PartsInfo(CURRENT_DIR.parent / 'p2ppcb_parts_data_f360' / parts_resolver.PARTS_INFO_DIRNAME, p)
                from reimport import APP_PACKAGES
                import pathlib
                if pi.check_separate_python(pathlib.Path(APP_PACKAGES)):
                    with open(SEPARATE_PYTHON_CONFIG_PATH, 'w') as f:
                        f.write(p)
                    set_separate_python(p)
                    con.ui.messageBox(f'The python interpreter path is stored to {SEPARATE_PYTHON_CONFIG_PATH}.', 'P2PPCB')
                else:
                    con.ui.messageBox('This python interpreter is not available. Is this Homebrew Python?\nPlease restart PC0.', 'P2PPCB')
                    return
            except Exception as e:
                import traceback
                msg = '\n'.join(traceback.format_exception(e))
                con.ui.messageBox(msg + '\nPlease restart PC0.', 'P2PPCB')
                return

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


def config_separate_python() -> str | None:
    import adsk.core as ac
    con = get_context()
    vs = f'{sys.version_info.major}.{sys.version_info.minor}'
    con.ui.messageBox(f'On macOS, PC0 requires Homebrew Python {vs}.\nPython.org is not available, just Homebrew.\nPlease choose the interpreter executable.', 'P2PPCB')
    file_dlg = con.ui.createFileDialog()
    file_dlg.isMultiSelectEnabled = False
    file_dlg.initialDirectory = str('/')
    file_dlg.title = f'Choose python{vs} file'
    file_dlg.filter = f'Executable File (python{vs})'
    if file_dlg.showOpen() != ac.DialogResults.DialogOK:
        con.ui.messageBox('Please restart PC0.', 'P2PPCB')
        return None
    return file_dlg.filename
