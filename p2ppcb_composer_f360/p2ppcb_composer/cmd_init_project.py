import pathlib
import typing as ty
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput
from f360_common import AN_KEY_PITCH_D, AN_KEY_PITCH_W, ANS_KEY_PITCH, CN_DEPOT_APPEARANCE, CN_DEPOT_PARTS, CN_FOOT, CN_INTERNAL, CURRENT_DIR, BadCodeException, CreateObjectCollectionT, F3Occurrence, \
    create_component, get_context, AN_PARTS_DATA_PATH
from p2ppcb_composer.cmd_common import AN_MAIN_KEY_V_OFFSET, AN_MAIN_LAYOUT_PLANE, AN_MAINBOARD, ANS_MAIN_OPTION, OnceEventHandler, all_has_sel_ins, \
    has_sel_in, get_cis, PartsCommandBlock, AN_MAIN_SURFACE, CommandHandlerBase, check_layout_plane
import mainboard
from route.route import get_cn_mainboard, get_mainboard_constants

INP_ID_MAIN_SURFACE_SEL = 'mainSurface'
INP_ID_MAIN_LAYOUT_PLANE_SEL = 'layoutPlane'
INP_ID_KEY_PITCH_W_VAL = 'keyPitchW'
INP_ID_KEY_PITCH_D_VAL = 'keyPitchD'
INP_ID_MAINBOARD = 'mainboard'
INP_ID_SCAFFOLD_BOOL = 'scaffold'

CN_SURFACE = 'Skeleton / Key Angle Surface'

TOOLTIPS_MAIN_SURFACE = ('Main Surface', 'Specify a surface. It becomes initial preference of skeleton surface and key angle surface of all keys.\nYou can change the choice afterwards, on each key individually.')
TOOLTIPS_MAIN_LAYOUT_PLANE = ('Main Layout Plane', 'Specify a construction plane to deploy a KLE file.\nYou can change the choice afterwards, on each key individually.')


def initialize():
    con = get_context()
    im = con.app.importManager

    def _import(o: F3Occurrence, fn: str, cn: str):
        if con.des.designType == af.DesignTypes.DirectDesignType:
            con.des.designType = af.DesignTypes.ParametricDesignType  # importToTarget() requires parametric design.
        with create_component(o.comp, cn):
            im.importToTarget(im.createFusionArchiveImportOptions(str(CURRENT_DIR / fn)), o.comp)

    inl_occ = con.child.get_real(CN_INTERNAL)
    if CN_DEPOT_APPEARANCE not in inl_occ.child:
        _import(inl_occ, 'appearance.f3d', CN_DEPOT_APPEARANCE)
    inl_occ.child[CN_DEPOT_APPEARANCE].light_bulb = False
    depot_parts_occ = inl_occ.child.get_real(CN_DEPOT_PARTS)
    cn_mainboard = get_cn_mainboard()
    if cn_mainboard not in depot_parts_occ.child:
        mc = get_mainboard_constants()
        _import(depot_parts_occ, mc.f3d_name, cn_mainboard)
    if CN_FOOT not in depot_parts_occ.child:
        _import(depot_parts_occ, 'Foot.f3d', CN_FOOT)
    depot_parts_occ.light_bulb = False

    if con.des.designType == af.DesignTypes.ParametricDesignType:
        con.des.designType = af.DesignTypes.DirectDesignType


def generate_scaffold():
    con = get_context()

    planes = con.root_comp.constructionPlanes
    cp_in = planes.createInput()
    cp_in.setByAngle(con.root_comp.yConstructionAxis, ac.ValueInput.createByString('10 degree'), con.root_comp.xYConstructionPlane)
    layout_base_plane = planes.add(cp_in)
    cp1_in = planes.createInput()
    cp1_in.setByOffset(layout_base_plane, ac.ValueInput.createByString('3 cm'))
    layout_plane = planes.add(cp1_in)
    layout_plane.name = 'Layout Plane'
    layout_base_plane.deleteMe()
    cp2_in = planes.createInput()
    cp2_in.setByAngle(con.root_comp.yConstructionAxis, ac.ValueInput.createByString('100 degree'), con.root_comp.xYConstructionPlane)
    profile_plane = planes.add(cp2_in)

    im = con.app.importManager
    skeleton_sketch = af.Sketch.cast(im.importToTarget2(im.createDXF2DImportOptions(str(CURRENT_DIR / 'scaffold_data/skeleton.dxf'), profile_plane), con.root_comp).item(0))
    skeleton_curves = CreateObjectCollectionT(af.SketchCurve)
    skeleton_curves.add(skeleton_sketch.sketchCurves.sketchControlPointSplines.item(0))
    skeleton_profile = con.root_comp.createOpenProfile(skeleton_curves, False)
    extrudes = con.root_comp.features.extrudeFeatures
    ex1_in = extrudes.createInput(skeleton_profile, af.FeatureOperations.NewBodyFeatureOperation)
    ex1_in.isSolid = False
    extent_cm4 = af.DistanceExtentDefinition.create(ac.ValueInput.createByString("4 cm"))
    ex1_in.setTwoSidesExtent(extent_cm4, extent_cm4)
    skeleton_surface = extrudes.add(ex1_in).bodies[0]
    skeleton_surface.opacity = 0.2
    skeleton_surface.name = 'Main Surface'
    skeleton_sketch.deleteMe()

    alternative_curves = CreateObjectCollectionT(af.SketchCurve)
    alternative_sketch = af.Sketch.cast(im.importToTarget2(im.createDXF2DImportOptions(str(CURRENT_DIR / 'scaffold_data/alternative.dxf'), profile_plane), con.root_comp).item(0))
    alternative_curves.add(alternative_sketch.sketchCurves.sketchControlPointSplines.item(0))
    alternative_profile = con.root_comp.createOpenProfile(alternative_curves, False)
    ex2_in = extrudes.createInput(alternative_profile, af.FeatureOperations.NewBodyFeatureOperation)
    ex2_in.isSolid = False
    ex2_in.setTwoSidesExtent(extent_cm4, extent_cm4)
    alternative_surface = extrudes.add(ex2_in).bodies[0]
    alternative_surface.opacity = 0.2
    alternative_surface.name = 'Alternative Surface (Key Angle or Skeleton)'
    alternative_sketch.deleteMe()
    profile_plane.deleteMe()

    so = con.child.get_real(CN_SURFACE)
    skeleton_surface = skeleton_surface.moveToComponent(so.raw_occ)
    alternative_surface = alternative_surface.moveToComponent(so.raw_occ)

    col = CreateObjectCollectionT(af.BRepBody)
    col.add(skeleton_surface)
    col.add(alternative_surface)
    reverse_normals = con.comp.features.reverseNormalFeatures
    _ = reverse_normals.add(col)

    moves = con.root_comp.features.moveFeatures
    tr = ac.Matrix3D.create()
    tr.translation = ac.Vector3D.create(0.0, -1.0, 0.0)
    move_in = moves.createInput(col, tr)
    moves.add(move_in)

    cp3_in = planes.createInput()
    cp3_in.setByOffset(con.root_comp.xYConstructionPlane, ac.ValueInput.createByString('-3 cm'))
    bridge_plane = planes.add(cp3_in)

    sk_bridge = con.root_comp.sketches.add(bridge_plane)
    sk_bridge.name = 'Bridge Profile'
    _ = sk_bridge.sketchCurves.sketchLines.addTwoPointRectangle(
        ac.Point3D.create(-3., -5.5, 0.),
        ac.Point3D.create(2., 5.5, 0.)
    )
    bridge_plane.deleteMe()

    layout_plane.displayBounds = ac.BoundingBox2D.create(
        ac.Point2D.create(-6., -4.), ac.Point2D.create(6., 4.), )

    pitch = 1.9
    offset = 0.

    return pitch, pitch, offset, skeleton_surface, alternative_surface, layout_plane


CUSTOM_EVENT_ID_INITIALIZE = 'initialize_project'


class InitializeEventHandler(OnceEventHandler):
    def __init__(self) -> None:
        super().__init__(CUSTOM_EVENT_ID_INITIALIZE)

    def notify_event(self):
        initialize()


class InitializeP2ppcbProjectCommandHandler(CommandHandlerBase):
    def __init__(self) -> None:
        super().__init__()
        self.parts_cb: PartsCommandBlock
        self.require_cn_internal = False
        self.require_cn_key_locators = False

    @property
    def cmd_name(self) -> str:
        return 'Initialize'

    @property
    def tooltip(self) -> str:
        return 'Initializes a P2PPCB project. It registers settings for a P2PPCB project. You can run this command two or more times.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/initialize'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()
        if con.des.designType == af.DesignTypes.ParametricDesignType:
            if con.ui.messageBox('P2PPCB requires direct modeling mode. The design is going to enter direct modeling mode.',
                                 'P2PPCB',
                                 ac.MessageBoxButtonTypes.OKCancelButtonType) != ac.DialogResults.DialogOK:
                self.create_ok = False
                return
            con.des.designType = af.DesignTypes.DirectDesignType

        main_in = self.inputs.addSelectionInput(INP_ID_MAIN_SURFACE_SEL, 'Main Surface', 'Select a surface')
        main_in.addSelectionFilter('SurfaceBodies')
        main_in.setSelectionLimits(1, 1)
        main_in.tooltip, main_in.tooltipDescription = TOOLTIPS_MAIN_SURFACE
        s = con.find_attrs(AN_MAIN_SURFACE)
        if len(s) == 1 and s[0].isValid and s[0].parent is not None:
            try:
                main_in.addSelection(s[0].parent)
            except:  # noqa
                pass

        layout_plane_in = self.inputs.addSelectionInput(INP_ID_MAIN_LAYOUT_PLANE_SEL, 'Main Layout Plane', 'Select a construction plane')
        layout_plane_in.addSelectionFilter('ConstructionPlanes')
        layout_plane_in.setSelectionLimits(1, 1)
        layout_plane_in.tooltip, layout_plane_in.tooltipDescription = TOOLTIPS_MAIN_LAYOUT_PLANE
        s = con.find_attrs(AN_MAIN_LAYOUT_PLANE)
        if len(s) == 1 and s[0].isValid and s[0].parent is not None:
            try:
                layout_plane_in.addSelection(s[0].parent)
            except:  # noqa
                pass

        attr: ty.MutableMapping[str, str] = con.child[CN_INTERNAL].comp_attr if CN_INTERNAL in con.child else {}
        pns = {AN_KEY_PITCH_W: 'Widthwise Key Pitch', AN_KEY_PITCH_D: 'Depthwise Key Pitch'}
        for an in ANS_KEY_PITCH:
            if an in attr:
                pitch_vi = ac.ValueInput.createByReal(float(attr[an]))
            else:
                pitch_vi = ac.ValueInput.createByString('19 mm')
            _ = self.inputs.addValueInput(an, pns[an], 'mm', pitch_vi)

        mb = attr[AN_MAINBOARD] if AN_MAINBOARD in attr else mainboard.DEFAULT
        mb_in = self.inputs.addDropDownCommandInput(INP_ID_MAINBOARD, 'Mainboard', ac.DropDownStyles.TextListDropDownStyle)
        for b in mainboard.BOARDS:
            mb_in.listItems.add(b, b == mb, '', -1)

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
        scaffold_in.tooltip = 'Start with a scaffold set instead of your own set.'
        if all_has_sel_ins([main_in, layout_plane_in]) and all([inp.selectedItem.name != '' for inp in self.parts_cb.get_option_ins()]):
            scaffold_in.isVisible = False

    def get_selection_ins(self) -> ty.Tuple[ac.SelectionCommandInput, ...]:
        return get_cis(self.inputs, [INP_ID_MAIN_SURFACE_SEL, INP_ID_MAIN_LAYOUT_PLANE_SEL], ac.SelectionCommandInput)

    def get_scaffold_in(self):
        return ac.BoolValueCommandInput.cast(self.inputs.itemById(INP_ID_SCAFFOLD_BOOL))

    def get_pitch_w_in(self):
        return ac.ValueCommandInput.cast(self.inputs.itemById(INP_ID_KEY_PITCH_W_VAL))

    def get_pitch_d_in(self):
        return ac.ValueCommandInput.cast(self.inputs.itemById(INP_ID_KEY_PITCH_D_VAL))

    def get_mainboard_in(self):
        return ac.DropDownCommandInput.cast(self.inputs.itemById(INP_ID_MAINBOARD))

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        if changed_input.id == INP_ID_SCAFFOLD_BOOL:
            scaffold_in = ac.BoolValueCommandInput.cast(changed_input)
            scaffold_disabled = not scaffold_in.value
            for ci in self.get_selection_ins() + self.parts_cb.get_option_ins() \
                    + (self.get_pitch_w_in(), self.get_pitch_d_in(), self.get_mainboard_in(), self.parts_cb.get_parts_data_in(), self.parts_cb.get_v_offset_in()):
                ci.isEnabled = scaffold_disabled
                ci.isVisible = scaffold_disabled
            for sci in self.get_selection_ins():
                c = 1 if scaffold_disabled else 0
                sci.setSelectionLimits(c, c)
        elif changed_input.id == INP_ID_MAIN_LAYOUT_PLANE_SEL:
            _, layout_plane_in = self.get_selection_ins()
            if has_sel_in(layout_plane_in):
                try:
                    _ = check_layout_plane(af.ConstructionPlane.cast(layout_plane_in.selection(0).entity))
                except Exception:
                    layout_plane_in.clearSelection()
        elif changed_input.id == INP_ID_MAIN_SURFACE_SEL:
            main_in, _ = self.get_selection_ins()
            if has_sel_in(main_in):
                ms = af.BRepBody.cast(main_in.selection(0).entity)
                if ms.assemblyContext is None:  # the surface is in the root component.
                    dr = get_context().ui.messageBox(
                        'Skeleton / Key angle surface should be in a separated component. Generate a component and move to it?',
                        'P2PPCB',
                        ac.MessageBoxButtonTypes.OKCancelButtonType)
                    if dr == ac.DialogResults.DialogCancel:
                        main_in.clearSelection()

        self.parts_cb.b_notify_input_changed(changed_input)

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs):
        self.parts_cb.notify_validate(event_args)

    def execute_common(self, event_args: CommandEventArgs, is_execute: bool):
        if self.get_scaffold_in().value:
            options = [inp.listItems[1].name for inp in self.parts_cb.get_option_ins()]
            pitch_w, pitch_d, offset, main_surface, _, layout_plane = generate_scaffold()
            mb = mainboard.DEFAULT
        else:
            main_in, layout_plane_in = self.get_selection_ins()
            main_surface = af.BRepBody.cast(main_in.selection(0).entity)
            layout_plane = af.ConstructionPlane.cast(layout_plane_in.selection(0).entity)

            pitch_w = self.get_pitch_w_in().value
            pitch_d = self.get_pitch_d_in().value

            options = self.parts_cb.get_selected_options()
            offset = self.parts_cb.get_v_offset()
            if offset is None:
                raise BadCodeException()
            mb = self.get_mainboard_in().selectedItem.name

        return pitch_w, pitch_d, offset, main_surface, layout_plane, options, mb

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args, False)
        con = get_context()
        if self.get_scaffold_in().value:
            camera = con.app.activeViewport.camera
            con.app.activeViewport.camera = camera

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        pitch_w, pitch_d, offset, main_surface, layout_plane, options, mb = self.execute_common(event_args, True)
        if main_surface.assemblyContext is None:  # the surface is in the root component.
            so = con.child.get_real(CN_SURFACE)
            main_surface = main_surface.moveToComponent(so.raw_occ)
        con.attr_singleton[AN_MAIN_SURFACE] = ('noop', main_surface)
        con.attr_singleton[AN_MAIN_LAYOUT_PLANE] = ('noop', layout_plane)

        inl_occ = con.child.get_real(CN_INTERNAL)
        inl_occ.comp_attr[AN_KEY_PITCH_W] = str(pitch_w)
        inl_occ.comp_attr[AN_KEY_PITCH_D] = str(pitch_d)
        inl_occ.comp_attr[AN_PARTS_DATA_PATH] = str(self.parts_cb.parts_data_path)
        for an, option in zip(ANS_MAIN_OPTION, options):
            inl_occ.comp_attr[an] = option
        inl_occ.comp_attr[AN_MAIN_KEY_V_OFFSET] = str(offset)
        inl_occ.comp_attr[AN_MAINBOARD] = mb

        InitializeEventHandler()
