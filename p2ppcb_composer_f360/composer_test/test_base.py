from typing import Optional, Type
import pathlib
import time
from PIL import Image as PILImageModule
from PIL.Image import Image
import adsk
import adsk.core as ac
import adsk.fusion as af
from f360_common import get_context, reset_context, F3Occurrence, create_component, CN_INTERNAL, AN_PARTS_DATA_PATH, PARTS_DATA_DIR
from p2ppcb_composer.cmd_common import CommandHandlerBase, get_ci
from adsk.core import CommandEventArgs, CommandCreatedEventArgs


HANDLERS = []


def do_many_events():
    for _ in range(200):
        adsk.doEvents()


def execute_command(cls: Type, is_block=False, is_terminate=True, **handler_args):
    join = False
    if is_block:
        def set_join():
            nonlocal join
            join = True
        exit = set_join
    elif is_terminate:
        adsk.autoTerminate(False)
        exit = adsk.terminate
    else:
        def nop():
            return
        exit = nop

    class Handler(cls):
        def notify_destroy(self, event_args) -> None:
            super().notify_destroy(event_args)
            try:
                HANDLERS.remove(self)
            except:  # noqa
                pass
            exit()

    handler_class = Handler

    con = get_context()

    cmd_defs: ac.CommandDefinitions = con.ui.commandDefinitions
    cmd_id = handler_class.__name__ + 'ButtonId'

    cmd_def: Optional[ac.CommandDefinition] = cmd_defs.itemById(cmd_id)
    if cmd_def is not None:
        cmd_def.deleteMe()
        cmd_def = cmd_defs.itemById(cmd_id)
        if cmd_def is not None:
            raise Exception(f'{cmd_id} deleteMe() failed.')
    cmd_def = cmd_defs.addButtonDefinition(cmd_id, handler_class.__name__, 'tooltip')
    
    # Connect to the command created event.
    handler: CommandHandlerBase = handler_class(**handler_args)
    cmd_def.commandCreated.add(handler)
    HANDLERS.append(handler)

    cmd_def.execute()

    if is_block:
        while not join:
            do_many_events()
    else:
        do_many_events()

    return handler


INP_ID_IMAGE_TEST = 'testImage'
INP_ID_IMAGE_ORACLE = 'oracleImage'
INP_ID_SAME_DIFFERENT = 'sameDifferent'


class ImageCompareCommandHandler(CommandHandlerBase):
    def __init__(self, test_img_path: pathlib.Path, oracle_path: pathlib.Path) -> None:
        super().__init__()
        self.test_img_path = test_img_path
        self.oracle_path = oracle_path
        self.is_same = False

        self.require_cn_internal = False
        self.require_cn_key_locators = False

    def notify_create(self, event_args: CommandCreatedEventArgs):
        test_img_in = self.inputs.addImageCommandInput(INP_ID_IMAGE_TEST, 'Test', str(self.test_img_path))
        test_img_in.isFullWidth = True
        oracle_in = self.inputs.addImageCommandInput(INP_ID_IMAGE_ORACLE, 'Oracle', str(self.oracle_path))
        oracle_in.isFullWidth = True
        result_in = self.inputs.addRadioButtonGroupCommandInput(INP_ID_SAME_DIFFERENT, 'Result')
        result_in.isFullWidth = True
        result_in.listItems.add('Same', False)
        result_in.listItems.add('Different', False)

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs):
        result_in = self.get_selection_in()
        for li in result_in.listItems:
            if li.isSelected:
                return
        event_args.areInputsValid = False

    def get_selection_in(self):
        return get_ci(self.inputs, INP_ID_SAME_DIFFERENT, ac.RadioButtonGroupCommandInput)

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        item = self.get_selection_in().selectedItem
        if item.name == 'Same':
            self.is_same = True


def compare_image_by_eyes(test_img: Image, oracle_path: pathlib.Path):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        test_img_path = pathlib.Path(d) / 'compare.png'
        test_img.save(test_img_path)
        handler = execute_command(ImageCompareCommandHandler, is_block=True, test_img_path=test_img_path, oracle_path=oracle_path)
        return handler.is_same


def capture_viewport():
    import tempfile

    app = get_context().app

    camera: ac.Camera = app.activeViewport.camera
    camera.viewOrientation = ac.ViewOrientations.TopViewOrientation
    camera.isFitView = True
    camera.isSmoothTransition = False
    app.activeViewport.camera = camera

    for _ in range(100):
        do_many_events()
        time.sleep(0.01)

    camera: ac.Camera = app.activeViewport.camera
    camera.isFitView = True
    camera.isSmoothTransition = False
    app.activeViewport.camera = camera

    for _ in range(100):
        do_many_events()
        time.sleep(0.01)

    tmp = tempfile.gettempdir()
    fn = str(pathlib.Path(tmp) / 'capture.png')
    app.activeViewport.saveAsImageFile(fn, 600, 600)
    img = PILImageModule.open(fn)

    return img


def new_document():
    con = get_context()
    doc = con.app.documents.add(ac.DocumentTypes.FusionDesignDocumentType)
    do_many_events()
    con = reset_context()
    con.des.designType = af.DesignTypes.DirectDesignType
    return doc


def open_test_document(f3d_file: pathlib.Path):
    con = get_context()
    im = con.app.importManager
    im_opt = im.createFusionArchiveImportOptions(str(f3d_file))
    doc = im.importToNewDocument(im_opt)
    do_many_events()
    con = reset_context()
    con.des.designType = af.DesignTypes.DirectDesignType
    con.child[CN_INTERNAL].comp_attr[AN_PARTS_DATA_PATH] = str(PARTS_DATA_DIR)
    return doc


def delete_document(name: str):
    '''
    F360 API cannot delete a file completely. So you need to restart F360 after using this function.
    '''
    con = get_context()
    folder: ac.DataFolder = con.app.data.dataProjects[0].rootFolder
    for _ in range(5):
        for ii in range(folder.dataFiles.count):
            try:
                f = folder.dataFiles[ii]
                adsk.doEvents()
            except Exception:
                time.sleep(.4)
                continue
            if f.name == name:
                f.deleteMe()
                return
        time.sleep(.4)
        adsk.doEvents()
    raise Exception(f'Cannot find document: {name}.')


class _Vertex:
    def __init__(self, v: af.BRepVertex) -> None:
        self.p = v.geometry
    
    def __hash__(self) -> int:
        hv = tuple((int(v * 100) for v in [self.p.x, self.p.y, self.p.z]))
        return hash(hv)
    
    def __eq__(self, v: object) -> bool:
        if not isinstance(v, _Vertex):
            return False
        return v.p.isEqualTo(self.p)


def is_same_brep_body(body: af.BRepBody, oracle: af.BRepBody):
    '''
    Just checks vertices.
    '''
    return body.volume == oracle.volume and {_Vertex(v) for v in body.vertices} == {_Vertex(v) for v in oracle.vertices}


def import_f3d(o: F3Occurrence, f3d_path: pathlib.Path, cn: str):
    con = get_context()
    if con.des.designType == af.DesignTypes.DirectDesignType:
        con.des.designType = af.DesignTypes.ParametricDesignType  # importToTarget() requires parametric design.
    im = con.app.importManager
    with create_component(o.comp, cn):
        im.importToTarget(im.createFusionArchiveImportOptions(str(f3d_path)), o.comp)
