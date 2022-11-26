import typing as ty
import adsk.core as ac
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput, SelectionEventArgs, SelectionCommandInput, Selection
import adsk.fusion as af
from f360_common import CN_KEY_LOCATORS, BadCodeException, get_context, CN_INTERNAL, F3Occurrence
from p2ppcb_composer.cmd_common import all_has_sel_ins, get_cis, has_sel_in, AN_LOCATORS_PLANE_TOKEN, TOOLTIP_NOT_SELECTED, InputLocators, \
    get_selected_locators, locator_notify_pre_select, CommandHandlerBase, CheckInterferenceCommandBlock, MoveComponentCommandBlock
from p2ppcb_composer.cmd_key_common import AN_LOCATORS_SKELETON_TOKEN, INP_ID_KEY_LOCATOR_SEL, INP_ID_LAYOUT_PLANE_SEL, AN_LOCATORS_ANGLE_TOKEN, get_layout_plane_transform, place_key_placeholders

INP_ID_SKELETON_SURFACE_SEL = 'skeletonSurface'
INP_ID_KEY_ANGLE_SURFACE_SEL = 'keyAngleSurface'


def get_lp(lp_in: ac.SelectionCommandInput):
    return af.ConstructionPlane.cast(lp_in.selection(0).entity)


def get_orig_lp(lp_in: ac.SelectionCommandInput, selected_locators: ty.List[F3Occurrence]):
    con = get_context()
    lp_ci = InputLocators(lp_in, AN_LOCATORS_PLANE_TOKEN)
    token = lp_ci.get_locators_attr_value(selected_locators)
    if token is None:
        raise BadCodeException('Locators have different lp.')
    return af.ConstructionPlane.cast(con.find_by_token(token)[0])


class MoveKeyCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()
        self.move_comp_cb: MoveComponentCommandBlock
        self.check_interference_cb: CheckInterferenceCommandBlock
        self.last_light_bulb = False

    @property
    def cmd_name(self) -> str:
        return 'Move Key'

    @property
    def tooltip(self) -> str:
        return "Moves keys via key locators. You can select key locators, not key placeholders. You can also change the layout plane, skeleton surface, or key angle surface of the keys. Inference check can require tens of seconds."

    @property
    def resource_folder(self) -> str:
        return 'Resources/move_key'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        inputs = self.inputs
        locator_in = inputs.addSelectionInput(INP_ID_KEY_LOCATOR_SEL, 'Key Locator', 'Select an entity')
        locator_in.addSelectionFilter('Occurrences')
        locator_in.setSelectionLimits(0, 0)

        layout_plane_in = inputs.addSelectionInput(INP_ID_LAYOUT_PLANE_SEL, 'Layout Plane', 'Select an entity')
        layout_plane_in.addSelectionFilter('ConstructionPlanes')
        layout_plane_in.setSelectionLimits(1, 1)
        layout_plane_in.isVisible = False

        skeleton_surface_in = inputs.addSelectionInput(INP_ID_SKELETON_SURFACE_SEL, 'Skeleton Surface', 'Select an entity')
        skeleton_surface_in.addSelectionFilter('SurfaceBodies')
        skeleton_surface_in.setSelectionLimits(1, 1)
        skeleton_surface_in.isVisible = False

        angle_surface_in = inputs.addSelectionInput(INP_ID_KEY_ANGLE_SURFACE_SEL, 'Key Angle Surface', 'Select an entity')
        angle_surface_in.addSelectionFilter('SurfaceBodies')
        angle_surface_in.setSelectionLimits(1, 1)
        angle_surface_in.isVisible = False

        inl_occ = get_context().child[CN_INTERNAL]
        inl_occ.light_bulb = True
        key_locators = inl_occ.child[CN_KEY_LOCATORS]
        self.last_light_bulb = key_locators.light_bulb
        key_locators.light_bulb = True

        self.move_comp_cb = MoveComponentCommandBlock(self)
        self.move_comp_cb.notify_create(event_args)

        self.check_interference_cb = CheckInterferenceCommandBlock(self)
        self.check_interference_cb.notify_create(event_args)

    def notify_pre_select(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        if active_input.id == INP_ID_KEY_LOCATOR_SEL:
            locator_notify_pre_select(INP_ID_KEY_LOCATOR_SEL, event_args, active_input, selection)
            return
        elif active_input.id == INP_ID_KEY_ANGLE_SURFACE_SEL:
            ent = af.BRepBody.cast(selection.entity)
        elif active_input.id == INP_ID_LAYOUT_PLANE_SEL:
            ent = af.ConstructionPlane.cast(selection.entity)
        else:
            return
        # ent.assemblyContext is None when the parentComponent is the root component.
        if ent is None or (ent.assemblyContext is not None and CN_INTERNAL in ent.assemblyContext.fullPathName):
            event_args.isSelectable = False

    def get_selection_ins(self) -> ty.Tuple[ac.SelectionCommandInput, ...]:
        return get_cis(self.inputs, [INP_ID_KEY_LOCATOR_SEL, INP_ID_LAYOUT_PLANE_SEL, INP_ID_SKELETON_SURFACE_SEL, INP_ID_KEY_ANGLE_SURFACE_SEL], ac.SelectionCommandInput)

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        locator_in, layout_plane_in, skeleton_surface_in, angle_surface_in = self.get_selection_ins()
        if_in = self.check_interference_cb.get_checkbox_ins()[0]
        selected_locators = get_selected_locators(locator_in)

        if changed_input.id == INP_ID_KEY_LOCATOR_SEL:
            lp_ci = InputLocators(layout_plane_in, AN_LOCATORS_PLANE_TOKEN)
            skeleton_ci = InputLocators(skeleton_surface_in, AN_LOCATORS_SKELETON_TOKEN)
            angle_ci = InputLocators(angle_surface_in, AN_LOCATORS_ANGLE_TOKEN)
            if not has_sel_in(locator_in):
                lp_ci.hide()
                skeleton_ci.hide()
                angle_ci.hide()
                if_in.isVisible = False
                if_in.value = False
            else:
                lp_ci.show_by_token(lp_ci.get_locators_attr_value(selected_locators))
                skeleton_ci.show(selected_locators)
                angle_ci.show(selected_locators)
                if_in.isVisible = True
                if_in.value = False
            self.check_interference_cb.show(if_in.value)
            locator_in.hasFocus = True
        elif changed_input.id in [INP_ID_LAYOUT_PLANE_SEL, INP_ID_KEY_ANGLE_SURFACE_SEL, INP_ID_SKELETON_SURFACE_SEL]:
            sci = ac.SelectionCommandInput.cast(changed_input)
            if not has_sel_in(sci):
                sci.tooltip = TOOLTIP_NOT_SELECTED
            else:
                sci.tooltip = sci.selection(0).entity.name  # type: ignore
        self.check_interference_cb.notify_input_changed(event_args, changed_input)

        if all_has_sel_ins([locator_in, layout_plane_in, skeleton_surface_in, angle_surface_in]):
            if changed_input.id == INP_ID_LAYOUT_PLANE_SEL or changed_input.id == INP_ID_KEY_LOCATOR_SEL:
                lp = get_lp(layout_plane_in)
                orig_lp = get_orig_lp(layout_plane_in, selected_locators)
                if not self.move_comp_cb.in_transaction() or lp != orig_lp:
                    t1 = get_layout_plane_transform(lp)
                    t2 = get_layout_plane_transform(orig_lp)
                    t2.invert()
                    mt = selected_locators[0].raw_occ.transform2.copy()
                    mt.transformBy(t2)
                    mt.transformBy(t1)
                    self.move_comp_cb.start_transaction(mt)
        else:
            self.move_comp_cb.stop_transaction()
        self.move_comp_cb.b_notify_changed_input(changed_input)

    def execute_common(self, event_args: CommandEventArgs) -> ty.List[F3Occurrence]:
        con = get_context()

        locator_in, lp_in, skeleton_surface_in, angle_in = self.get_selection_ins()
        angle = af.BRepBody.cast(angle_in.selection(0).entity)  # Don't move downward this line because CommandInput losses the selection by manipulating components.
        if has_sel_in(locator_in):
            selected_locators = get_selected_locators(locator_in)

            lp_ci = InputLocators(lp_in, AN_LOCATORS_PLANE_TOKEN)
            lp = get_lp(lp_in)
            token = lp_ci.get_locators_attr_value(selected_locators)
            if token is None:
                raise BadCodeException('Locators have different lp.')
            orig_lp = af.ConstructionPlane.cast(con.find_by_token(token)[0])
            if lp != orig_lp:
                orig_t = get_layout_plane_transform(orig_lp)
                new_t = get_layout_plane_transform(lp)
                orig_t.invert()
                for o in selected_locators:
                    t = o.transform.copy()
                    t.transformBy(orig_t)
                    t.transformBy(new_t)
                    o.transform = t
                lp_ci.set_locators_attr_value(selected_locators, lp.entityToken)

            skeleton_ci = InputLocators(skeleton_surface_in, AN_LOCATORS_SKELETON_TOKEN)
            skeleton_surface = af.BRepBody.cast(skeleton_surface_in.selection(0).entity)
            token = skeleton_ci.get_locators_attr_value(selected_locators)
            if skeleton_surface.entityToken != token:
                skeleton_ci.set_locators_attr_value(selected_locators, skeleton_surface.entityToken)

            angle_ci = InputLocators(angle_in, AN_LOCATORS_ANGLE_TOKEN)
            token = angle_ci.get_locators_attr_value(selected_locators)
            if angle.entityToken != token:
                angle_ci.set_locators_attr_value(selected_locators, angle.entityToken)

            self.move_comp_cb.b_notify_execute_preview(event_args, selected_locators)
            place_key_placeholders(selected_locators)  # type: ignore
            return selected_locators
        return []

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        selected_locators = self.execute_common(event_args)
        self.check_interference_cb.b_notify_execute_preview(selected_locators)

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        _ = self.execute_common(event_args)
        # Too slow
        # selected_kpns: ty.Set[str] = set()
        # for kl_occ in selected_locators:
        #     pattern_name = kl_occ.comp_attr[AN_LOCATORS_PATTERN_NAME]
        #     i = int(kl_occ.comp_attr[AN_LOCATORS_I])
        #     selected_kpns.add(key_placeholder_name(i, pattern_name))
        # result = self.check_interference_cb.check_key_placeholders(selected_kpns)
        # if result is None:
        #     return
        # hit_mev, hit_hole, hit_mf, hit_kpns, cache_temp_body = result
        # for _, tb in cache_temp_body:
        #     tb.deleteMe()
        # n_hit = len(hit_mev) + len(hit_hole) + len(hit_mf)
        # if n_hit > 0:
        #     get_context().ui.messageBox(f'Warning: {n_hit} interference(s) exists among {len(hit_kpns)} key placeholder(s).')

    def notify_destroy(self, event_args: CommandEventArgs) -> None:
        key_locators = get_context().child[CN_INTERNAL].child[CN_KEY_LOCATORS]
        key_locators.light_bulb = self.last_light_bulb


class SyncKeyCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()

    @property
    def cmd_name(self) -> str:
        return 'Sync Key'

    @property
    def tooltip(self) -> str:
        return "Synchronizes all key placeholders to their skeleton/angle surfaces. Run this command after you modified skeleton/angle surfaces."

    @property
    def resource_folder(self) -> str:
        return 'Resources/sync_key'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        place_key_placeholders(None)
