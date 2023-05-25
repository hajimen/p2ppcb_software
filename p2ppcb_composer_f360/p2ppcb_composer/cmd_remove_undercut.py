import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput
from f360_common import get_context, CreateObjectCollectionT
from p2ppcb_composer.cmd_common import CommandHandlerBase, get_cis


INP_ID_UNDERCUT_SURFACE_SEL = 'undercutSurface'
INP_ID_FRAME_BODY_SEL = 'frameBody'
INP_ID_PREVIEW_BOOL = 'preview'


class RemoveUndercutCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.require_cn_internal = False
        self.require_cn_key_locators = False

    @property
    def cmd_name(self) -> str:
        return 'Remove Undercut'

    @property
    def tooltip(self) -> str:
        return "Removes undercuts of a cover in a command. Make a sketch line (long enough) which shows the pull/insert direction of the frame. Choose the line and undercut surfaces."

    @property
    def resource_folder(self) -> str:
        return 'Resources/remove_undercut'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        inputs = self.inputs
        frame_in = inputs.addSelectionInput(INP_ID_FRAME_BODY_SEL, 'Frame', 'Select Frame body')
        frame_in.addSelectionFilter('SolidBodies')
        frame_in.setSelectionLimits(1, 1)

        undercut_in = inputs.addSelectionInput(INP_ID_UNDERCUT_SURFACE_SEL, 'Undercut Surfaces', 'Select undercut surfaces')
        undercut_in.addSelectionFilter('SolidFaces')
        undercut_in.setSelectionLimits(1, 0)

        preview_in = self.inputs.addBoolValueInput(INP_ID_PREVIEW_BOOL, 'Show Preview', True)
        preview_in.tooltip = 'Show preview of the command result.'

    def get_selection_ins(self) -> tuple[ac.SelectionCommandInput, ...]:
        return get_cis(self.inputs, [INP_ID_FRAME_BODY_SEL, INP_ID_UNDERCUT_SURFACE_SEL], ac.SelectionCommandInput)

    def get_preview_in(self):
        return ac.BoolValueCommandInput.cast(self.inputs.itemById(INP_ID_PREVIEW_BOOL))

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        pass

    def execute_common(self, event_args: CommandEventArgs) -> None:
        con = get_context()

        lines = con.comp.sketches.add(con.comp.xYConstructionPlane).sketchCurves.sketchLines
        frame_in, undercut_in = self.get_selection_ins()
        frame = af.BRepBody.cast(frame_in.selection(0).entity)
        undercuts = [af.BRepFace.cast(undercut_in.selection(i).entity) for i in range(undercut_in.selectionCount)]
        sweeps = con.root_comp.features.sweepFeatures
        col = CreateObjectCollectionT(af.BRepBody)
        z = ac.Vector3D.create(0, 0, 100)
        for uc in undercuts:
            sp = uc.vertices[0].geometry
            ep = sp.copy()
            ep.translateBy(z)
            line = lines.addByTwoPoints(sp, ep)
            p = af.Path.create(line, af.ChainedCurveOptions.noChainedCurves)
            sweep_in = sweeps.createInput(uc, p, af.FeatureOperations.NewBodyFeatureOperation)
            sf = sweeps.add(sweep_in)
            col.add(sf.bodies[0])
        combines = con.comp.features.combineFeatures
        combine_in = combines.createInput(frame, col)
        combine_in.operation = af.FeatureOperations.CutFeatureOperation
        combines.add(combine_in)

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        if self.get_preview_in().value:
            self.execute_common(event_args)
            event_args.isValidResult = True

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common(event_args)
