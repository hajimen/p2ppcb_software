from typing import Optional, Any, Type
import pathlib
import time
from PIL import Image
import adsk
import adsk.core as ac
import adsk.fusion as af
from f360_common import get_context, reset_context, F3Occurrence, create_component
from p2ppcb_composer.cmd_common import CommandHandlerBase


HANDLERS = []
HANDLER_IDS = []


def do_many_events():
    for _ in range(200):
        adsk.doEvents()


def execute_command(cls: Type):
    class Handler(cls):
        def notify_destroy(self, event_args) -> None:
            super().notify_destroy(event_args)
            adsk.terminate()

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
    handler: CommandHandlerBase = handler_class()
    cmd_def.commandCreated.add(handler)
    HANDLERS.append(handler)

    cmd_def.execute()
    do_many_events()


def compare_image_by_eyes(test_img: Any, oracle_path: pathlib.Path):
    import tkinter as tk
    from PIL import ImageTk
    right_img = Image.open(oracle_path)

    class Application(tk.Frame):
        def __init__(self, master=None):
            super().__init__(master)
            self.master = master  # type: ignore
            self.pack()
            self.create_widgets()
            self.was_same = False

        def create_widgets(self):
            self.left_canvas = tk.Canvas(self, width=test_img.width, height=test_img.height)
            self.left_canvas.grid(row=0, column=0)

            self.right_canvas = tk.Canvas(self, width=right_img.width, height=right_img.height)
            self.right_canvas.grid(row=0, column=1)

            l_im = ImageTk.PhotoImage(master=self.left_canvas, image=test_img)  # type: ignore
            self.left_canvas.photo = l_im  # type: ignore
            self.left_canvas.create_image(0, 0, anchor='nw', image=self.left_canvas.photo)  # type: ignore

            r_im = ImageTk.PhotoImage(master=self.right_canvas, image=right_img)  # type: ignore
            self.right_canvas.photo = r_im  # type: ignore
            self.right_canvas.create_image(0, 0, anchor='nw', image=self.right_canvas.photo)  # type: ignore

            self.button_frame = tk.Frame(self, width=right_img.width, height=30)
            self.button_frame.grid(row=1, column=1)

            self.same = tk.Button(self.button_frame)
            self.same["text"] = "Same"
            self.same["command"] = self.handle_same
            self.same.pack(side="right")

            self.different = tk.Button(self.button_frame)
            self.different["text"] = "Different"
            self.different["command"] = self.handle_different
            self.different.pack(side="left")

        def handle_same(self):
            self.was_same = True
            self.master.destroy()

        def handle_different(self):
            self.master.destroy()

    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()

    return app.was_same


def capture_viewport():
    import tempfile

    app = get_context().app

    camera: ac.Camera = app.activeViewport.camera
    camera.viewOrientation = ac.ViewOrientations.IsoTopLeftViewOrientation
    camera.isSmoothTransition = False
    app.activeViewport.camera = camera
    camera = app.activeViewport.camera
    camera.isFitView = True
    camera.isSmoothTransition = False
    app.activeViewport.camera = camera

    tmp = tempfile.gettempdir()
    fn = str(pathlib.Path(tmp) / 'capture.png')
    app.activeViewport.saveAsImageFile(fn, 600, 600)
    img = Image.open(fn)

    return img


def new_document():
    con = get_context()
    doc = con.app.documents.add(ac.DocumentTypes.FusionDesignDocumentType)
    for _ in range(10):
        adsk.doEvents()
    con = reset_context()
    con.des.designType = af.DesignTypes.DirectDesignType
    return doc


def open_test_document(f3d_file: pathlib.Path):
    con = get_context()
    im = con.app.importManager
    im_opt = im.createFusionArchiveImportOptions(str(f3d_file))
    doc = im.importToNewDocument(im_opt)
    for _ in range(10):
        adsk.doEvents()
    con = reset_context()
    con.des.designType = af.DesignTypes.DirectDesignType
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
