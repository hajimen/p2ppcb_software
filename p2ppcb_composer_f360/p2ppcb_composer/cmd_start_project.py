import pathlib
import typing as ty
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput
from f360_common import CN_DEPOT_APPEARANCE, CN_DEPOT_PARTS, CN_FOOT, CN_INTERNAL, CN_MAINBOARD_ALICE, CURRENT_DIR, CreateObjectCollectionT, \
    AN_KEY_PITCH, create_component, get_context, AN_PARTS_DATA_PATH
from p2ppcb_composer.cmd_common import AN_MAIN_KEY_V_OFFSET, AN_MAIN_LAYOUT_PLANE, ANS_MAIN_OPTION, OnceEventHandler, \
    has_sel_in, get_cis, PartsCommandBlock, AN_SKELETON_SURFACE, CommandHandlerBase, check_layout_plane

INP_ID_SKELETON_SURFACE_SEL = 'skeletonSurface'
INP_ID_MAIN_LAYOUT_PLANE_SEL = 'layoutPlane'
INP_ID_KEY_PITCH_VAL = 'keyPitch'
INP_ID_SCAFFOLD_BOOL = 'scaffold'


def _set_design_type():
    con = get_context()
    if con.des.designType == af.DesignTypes.DirectDesignType:
        con.des.designType = af.DesignTypes.ParametricDesignType  # importToTarget() requires parametric design.


def initialize():
    con = get_context()
    inl_occ = con.child[CN_INTERNAL]
    im = con.app.importManager
    if CN_DEPOT_APPEARANCE not in inl_occ.child:
        _set_design_type()
        with create_component(inl_occ.comp, CN_DEPOT_APPEARANCE):
            im.importToTarget(im.createFusionArchiveImportOptions(str(CURRENT_DIR / 'appearance.f3d')), inl_occ.comp)
    inl_occ.child[CN_DEPOT_APPEARANCE].light_bulb = False
    depot_parts_occ = inl_occ.child.get_real(CN_DEPOT_PARTS)
    if CN_MAINBOARD_ALICE not in depot_parts_occ.child:
        _set_design_type()
        with create_component(depot_parts_occ.comp, CN_MAINBOARD_ALICE):
            im.importToTarget(im.createFusionArchiveImportOptions(str(CURRENT_DIR / 'Alice.f3d')), depot_parts_occ.comp)
    if CN_FOOT not in depot_parts_occ.child:
        _set_design_type()
        with create_component(depot_parts_occ.comp, CN_FOOT):
            im.importToTarget(im.createFusionArchiveImportOptions(str(CURRENT_DIR / 'Foot.f3d')), depot_parts_occ.comp)
    depot_parts_occ.light_bulb = False
    if con.des.designType == af.DesignTypes.ParametricDesignType:
        con.des.designType = af.DesignTypes.DirectDesignType


def generate_scaffold():
    con = get_context()

    sk = con.root_comp.sketches.add(con.root_comp.yZConstructionPlane)
    sk.name = 'P2PPCB internal (Scaffold set)'
    sk.isVisible = False
    arcs = sk.sketchCurves.sketchArcs
    arc1 = arcs.addByThreePoints(
        ac.Point3D.create(-2.5, -4. - 1.4, 0.),
        ac.Point3D.create(-2., - 1.4, 0.),
        ac.Point3D.create(-3., 7. - 1.4, 0.))
    profile1 = con.root_comp.createOpenProfile(arc1, False)

    extrudes = con.root_comp.features.extrudeFeatures
    ex_in1 = extrudes.createInput(profile1, af.FeatureOperations.NewBodyFeatureOperation)
    ex_in1.isSolid = False
    cm15 = ac.ValueInput.createByString("15 cm")
    ex_in1.setTwoSidesDistanceExtent(cm15, cm15)
    skeleton_surface = extrudes.add(ex_in1).bodies.item(0)
    skeleton_surface.opacity = 0.2

    arc2 = arcs.addByThreePoints(
        ac.Point3D.create(-4., -4. - 1.4, 0.),
        ac.Point3D.create(-3., - 1.4, 0.),
        ac.Point3D.create(-5., 7. - 1.4, 0.))
    profile2 = con.root_comp.createOpenProfile(arc2, False)
    ex_in2 = extrudes.createInput(profile2, af.FeatureOperations.NewBodyFeatureOperation)
    ex_in2.isSolid = False
    ex_in2.setTwoSidesDistanceExtent(cm15, cm15)
    alternative_surface = extrudes.add(ex_in2).bodies.item(0)
    alternative_surface.opacity = 0.2
    alternative_surface.name = 'Alternative Surface (Key Angle or Skeleton)'

    col = CreateObjectCollectionT(af.BRepBody)
    col.add(skeleton_surface)
    col.add(alternative_surface)
    reverse_normals = con.comp.features.reverseNormalFeatures
    _ = reverse_normals.add(col)

    sp = sk.sketchPoints
    planes = con.root_comp.constructionPlanes
    cp_in = planes.createInput()
    cp_in.setByThreePoints(
        # sp.add(ac.Point3D.create(-5., -4. - 1.4, -15.)),
        # sp.add(ac.Point3D.create(-5., -4. - 1.4, 1.)),
        # sp.add(ac.Point3D.create(-5.5, 7. - 1.4, 0.)))
        sp.add(ac.Point3D.create(-15., -4. - 1.4, 5.)),
        sp.add(ac.Point3D.create(1., -4. - 1.4, 5.)),
        sp.add(ac.Point3D.create(0., 7. - 1.4, 5.5)))
    layout_plane = planes.add(cp_in)
    layout_plane.displayBounds = ac.BoundingBox2D.create(
        ac.Point2D.create(0., 0.), ac.Point2D.create(30., 11.), )

    pitch = 1.9
    offset = 0.

    sk_bridge = con.root_comp.sketches.add(con.root_comp.xYConstructionPlane)
    sk_bridge.name = 'Bridge Profile'
    _ = sk_bridge.sketchCurves.sketchLines.addTwoPointRectangle(
        ac.Point3D.create(-14., -4., 0.),
        ac.Point3D.create(14., 4., 0.)
    )

    camera = con.app.activeViewport.camera
    camera.isFitView = True
    con.app.activeViewport.camera = camera

    return pitch, offset, skeleton_surface, alternative_surface, layout_plane


CUSTOM_EVENT_ID_INITIALIZE = 'initialize_project'


class InitializeEventHandler(OnceEventHandler):
    def __init__(self) -> None:
        super().__init__(CUSTOM_EVENT_ID_INITIALIZE)

    def notify_event(self):
        initialize()


class StartP2ppcbProjectCommandHandler(CommandHandlerBase):
    def __init__(self) -> None:
        super().__init__()
        self.parts_cb: PartsCommandBlock

    @property
    def cmd_name(self) -> str:
        return 'Start'

    @property
    def tooltip(self) -> str:
        return 'Starts a P2PPCB Project. It initializes a file and registers settings for a P2PPCB project.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/start'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()
        if con.des.designType == af.DesignTypes.ParametricDesignType:
            if con.ui.messageBox('P2PPCB requires direct modeling mode. The design is going to enter direct modeling mode.',
                                 'P2PPCB',
                                 ac.MessageBoxButtonTypes.OKCancelButtonType) != ac.DialogResults.DialogOK:
                self.run_execute = False
                return

        skeleton_in = self.inputs.addSelectionInput(INP_ID_SKELETON_SURFACE_SEL, 'Skeleton Surface', 'Select an entity')
        skeleton_in.addSelectionFilter('SurfaceBodies')
        skeleton_in.setSelectionLimits(1, 1)
        s = con.find_attrs(AN_SKELETON_SURFACE)
        if len(s) == 1:
            skeleton_in.addSelection(s[0].parent)

        layout_plane_in = self.inputs.addSelectionInput(INP_ID_MAIN_LAYOUT_PLANE_SEL, 'Main Layout Plane', 'Select an entity')
        layout_plane_in.addSelectionFilter('ConstructionPlanes')
        layout_plane_in.setSelectionLimits(1, 1)
        s = con.find_attrs(AN_MAIN_LAYOUT_PLANE)
        if len(s) == 1:
            layout_plane_in.addSelection(s[0].parent)

        attr: ty.MutableMapping[str, str] = con.child[CN_INTERNAL].comp_attr if CN_INTERNAL in con.child else {}
        if AN_KEY_PITCH in attr:
            pitch_vi = ac.ValueInput.createByReal(float(attr[AN_KEY_PITCH]))
        else:
            pitch_vi = ac.ValueInput.createByString('19 mm')
        _ = self.inputs.addValueInput(INP_ID_KEY_PITCH_VAL, 'Key Pitch', 'mm', pitch_vi)

        self.parts_cb = PartsCommandBlock(self)
        self.parts_cb.notify_create(event_args)
        if AN_PARTS_DATA_PATH in attr:
            self.parts_cb.set_parts_data_path(pathlib.Path(attr[AN_PARTS_DATA_PATH]))

        for an, inp in zip(ANS_MAIN_OPTION, self.parts_cb.get_option_ins()):
            if an in attr:
                desc = attr[an]
                hit = False
                for item in inp.listItems:
                    item.isSelected = (item.name == desc)
                    hit = True
                if not hit:
                    inp.listItems[0].isSelected = True

        scaffold_in = self.inputs.addBoolValueInput(INP_ID_SCAFFOLD_BOOL, 'Generate a scaffold set', True)
        scaffold_in.tooltip = 'Start with a scaffold set instead of your original set.'
        if skeleton_in.selectionCount > 0 and layout_plane_in.selectionCount > 0 and all([inp.selectedItem.name != '' for inp in self.parts_cb.get_option_ins()]):
            scaffold_in.isVisible = False

    def get_selection_ins(self) -> ty.Tuple[ac.SelectionCommandInput, ...]:
        return get_cis(self.inputs, [INP_ID_SKELETON_SURFACE_SEL, INP_ID_MAIN_LAYOUT_PLANE_SEL], ac.SelectionCommandInput)

    def get_scaffold_in(self):
        return ac.BoolValueCommandInput.cast(self.inputs.itemById(INP_ID_SCAFFOLD_BOOL))

    def get_pitch_in(self):
        return ac.ValueCommandInput.cast(self.inputs.itemById(INP_ID_KEY_PITCH_VAL))

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        if changed_input.id == INP_ID_SCAFFOLD_BOOL:
            scaffold_in = ac.BoolValueCommandInput.cast(changed_input)
            scaffold_disabled = not scaffold_in.value
            for ci in self.get_selection_ins() + self.parts_cb.get_option_ins() \
                    + (self.get_pitch_in(), self.parts_cb.get_parts_data_in(), self.parts_cb.get_v_offset_in()):
                ci.isEnabled = scaffold_disabled
                ci.isVisible = scaffold_disabled
            for sci in self.get_selection_ins():
                c = 1 if scaffold_disabled else 0
                sci.setSelectionLimits(c, c)
            self.inputs.command.doExecutePreview()
        elif changed_input.id == INP_ID_MAIN_LAYOUT_PLANE_SEL:
            _, layout_plane_in = self.get_selection_ins()
            if has_sel_in(layout_plane_in):
                try:
                    _ = check_layout_plane(af.ConstructionPlane.cast(layout_plane_in.selection(0).entity))
                except Exception:
                    layout_plane_in.clearSelection()
        self.parts_cb.b_notify_input_changed(changed_input)

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs):
        self.parts_cb.notify_validate(event_args)

    def execute_common(self, event_args: CommandEventArgs) -> None:
        print('executePreview')
        con = get_context()
        con.des.designType = af.DesignTypes.DirectDesignType

        if self.get_scaffold_in().value:
            options = [inp.listItems.item(1).name for inp in self.parts_cb.get_option_ins()]
            pitch, offset, skeleton_surface, _, layout_plane = generate_scaffold()
        else:
            skeleton_in, layout_plane_in = self.get_selection_ins()
            skeleton_surface = af.BRepBody.cast(skeleton_in.selection(0).entity)
            layout_plane = af.ConstructionPlane.cast(layout_plane_in.selection(0).entity)
            pitch = self.get_pitch_in().value

            options = self.parts_cb.get_selected_options()
            offset = self.parts_cb.get_v_offset()
            if offset is None:
                raise Exception('Bad code.')

        con.attr_singleton[AN_SKELETON_SURFACE] = ('noop', skeleton_surface)
        con.attr_singleton[AN_MAIN_LAYOUT_PLANE] = ('noop', layout_plane)
        inl_occ = con.child.get_real(CN_INTERNAL)
        inl_occ.comp_attr[AN_KEY_PITCH] = str(pitch)
        inl_occ.comp_attr[AN_PARTS_DATA_PATH] = str(self.parts_cb.parts_data_path)
        for an, option in zip(ANS_MAIN_OPTION, options):
            inl_occ.comp_attr[an] = option
        inl_occ.comp_attr[AN_MAIN_KEY_V_OFFSET] = str(offset)

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
        InitializeEventHandler()

    def notify_destroy(self, event_args: CommandEventArgs) -> None:
        print('destroy')
