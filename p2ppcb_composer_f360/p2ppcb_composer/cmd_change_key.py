import typing as ty
from pint import Quantity
import p2ppcb_parts_resolver.resolver as parts_resolver
import adsk.fusion as af
import adsk.core as ac
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput, SelectionEventArgs, SelectionCommandInput, Selection
from f360_common import AN_KEY_V_OFFSET, AN_LOCATORS_ENABLED, AN_LOCATORS_PATTERN_NAME, AN_LOCATORS_SPECIFIER, AN_PARTS_DATA_PATH, ANS_OPTION, CN_KEY_LOCATORS, \
    CN_KEY_PLACEHOLDERS, CURRENT_DIR, BadCodeException, BadConditionException, FourOrientation, SpecsOpsOnPn, TwoOrientation, VirtualF3Occurrence, \
    AN_KLE_B64, get_context, CN_INTERNAL, key_placeholder_name, load_kle_by_b64, get_part_info, get_parts_data_path
import p2ppcb_parts_depot.depot as parts_depot
from p2ppcb_composer.cmd_common import CommandHandlerBase, PartsCommandBlock, \
    get_ci, has_sel_in, get_selected_locators, locator_notify_pre_select, OnceEventHandler
from p2ppcb_composer.cmd_key_common import INP_ID_KEY_LOCATOR_SEL, I_ANS_OPTION, PP_KEY_ASSEMBLY_ON_SO, PrepareKeyAssemblyParameter, PrepareKeyPlaceholderParameter, \
    place_key_placeholders, prepare_key_assembly, fill_surrogate, prepare_parts_sync

INP_ID_SPECIFIER_STR = 'specifier'
INP_ID_PATTERN_NAME_STR = 'patternName'
INP_ID_ENABLE_BOOL = 'enable'

TOOLTIP_SPECIFIER = "Row-dependent caps should have prefix on pattern name, like 'R4 1u'. 'Homing' and 'Spacebar' are common prefix."
TOOLTIP_PATTERN_NAME = "Usually '1u', '125u', '15u' and so on. There are some special pattern names too, like 'ISO Enter'."

CUSTOM_EVENT_ID_PREPARE_PARTS = 'prepare_parts'


class PreparePartsEventHandler(OnceEventHandler):
    def __init__(self, pps_part: ty.List[parts_depot.PreparePartParameter]) -> None:
        self.pps_part = pps_part
        super().__init__(CUSTOM_EVENT_ID_PREPARE_PARTS)

    def notify_event(self):
        prepare_parts_sync(self.pps_part)


class ChangedLocatorException(Exception):
    def __init__(self, available_specifiers: ty.List[str]) -> None:
        super().__init__()
        self.available_specifiers = available_specifiers


class ChangeKeyDescsCommandHandler(CommandHandlerBase):
    def __init__(self) -> None:
        super().__init__()
        self.parts_cb: PartsCommandBlock
        self.pi: parts_resolver.PartsInfo
        self.specs_ops_on_pn: SpecsOpsOnPn
        self.once_shown: ty.Set[str]
        self.last_light_bulb = False

    @property
    def cmd_name(self) -> str:
        return 'Change Key'

    @property
    def tooltip(self) -> str:
        return "Changes key assemblies, i.e. the orientation, the vertical alignment, the types of the parts. You can select key locators, not key placeholders. You cannot change key pattern, i.e. '2u', 'ISO Enter'. You cannot see preview of changed key assemblies when you specify unused parts."  # noqa

    @property
    def resource_folder(self) -> str:
        return 'Resources/change_key'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        self.parts_cb = PartsCommandBlock(self, get_parts_data_path())
        self.pi = get_part_info()
        kle_b64 = get_context().child[CN_INTERNAL].comp_attr[AN_KLE_B64]
        self.specs_ops_on_pn = load_kle_by_b64(kle_b64, self.pi)[0]
        self.once_shown = set()

        locator_in = self.inputs.addSelectionInput(INP_ID_KEY_LOCATOR_SEL, 'Key Locator', 'Select an entity')
        locator_in.addSelectionFilter('Occurrences')
        locator_in.setSelectionLimits(0, 0)

        specifier_in = self.inputs.addStringValueInput(INP_ID_SPECIFIER_STR, 'Specifier', '')
        specifier_in.isVisible = False

        enable_in = self.inputs.addBoolValueInput(INP_ID_ENABLE_BOOL, 'Enable', True)
        enable_in.isVisible = False

        inl_occ = get_context().child[CN_INTERNAL]
        inl_occ.light_bulb = True
        key_locators = inl_occ.child[CN_KEY_LOCATORS]
        self.last_light_bulb = key_locators.light_bulb
        key_locators.light_bulb = True

        self.parts_cb.notify_create(event_args)
        self.parts_cb.show_hide(False)

    def get_selection_in(self):
        return get_ci(self.inputs, INP_ID_KEY_LOCATOR_SEL, ac.SelectionCommandInput)

    def get_specifier_in(self):
        return get_ci(self.inputs, INP_ID_SPECIFIER_STR, ac.StringValueCommandInput)

    def get_enable_in(self):
        return get_ci(self.inputs, INP_ID_ENABLE_BOOL, ac.BoolValueCommandInput)

    def notify_pre_select(self, event_args: SelectionEventArgs, active_input: SelectionCommandInput, selection: Selection) -> None:
        if active_input.id == INP_ID_KEY_LOCATOR_SEL:
            locator_notify_pre_select(INP_ID_KEY_LOCATOR_SEL, event_args, active_input, selection)

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        locator_in = self.get_selection_in()
        specifier_in = self.get_specifier_in()
        enable_in = self.get_enable_in()
        selected_locators = get_selected_locators(locator_in)
        if changed_input.id == INP_ID_KEY_LOCATOR_SEL:
            self.parts_cb.deselect()
            if has_sel_in(locator_in):
                self.parts_cb.show_hide(True)
                specifier_in.isVisible = True
                enable_in.isVisible = True
                last_options: ty.List[ty.Optional[str]] = [None for _ in ANS_OPTION]
                last_specifier: ty.Optional[str] = None
                last_offset_str: ty.Optional[str] = None
                last_pn: ty.Optional[str] = None
                sames = [True for _ in ANS_OPTION]
                same_specifier = True
                same_offset = True
                same_pn = True
                for kl_occ in selected_locators:
                    for i, an in enumerate(ANS_OPTION):
                        option = kl_occ.comp_attr[an]
                        sames[i] = sames[i] and (last_options[i] is None or option == last_options[i])
                        last_options[i] = option
                    specifier = kl_occ.comp_attr[AN_LOCATORS_SPECIFIER]
                    same_specifier = same_specifier and (last_specifier is None or specifier == last_specifier)
                    last_specifier = specifier

                    offset_str = kl_occ.comp_attr[AN_KEY_V_OFFSET]
                    same_offset = same_offset and (last_offset_str is None or offset_str == last_offset_str)
                    last_offset_str = offset_str

                    pn = kl_occ.comp_attr[AN_LOCATORS_PATTERN_NAME]
                    same_pn = same_pn and (last_pn is None or pn == last_pn)
                    last_pn = pn
                if last_specifier is None:
                    raise BadCodeException()
                for option, inp, same in zip(last_options, self.parts_cb.get_option_ins(), sames):
                    if not same:
                        option = ''
                    for li in inp.listItems:
                        if li.name == option:
                            li.isSelected = True
                            break
                vo_in = self.parts_cb.get_v_offset_in()
                if same_offset and last_offset_str is not None:
                    vo_in.value = f'{float(last_offset_str) * 10} mm'
                else:
                    vo_in.value = ''
                specifier_in.value = last_specifier if same_specifier else ''
                specifier_in.isEnabled = same_pn
                enable_in.value = bool(selected_locators[0].comp_attr[AN_LOCATORS_ENABLED])
            else:
                self.parts_cb.show_hide(False)
                self.get_specifier_in().isVisible = False
            locator_in.hasFocus = True

        self.parts_cb.b_notify_input_changed(changed_input)

    def get_selected_specifier_options_offset_enable(self):
        offset_str = self.parts_cb.get_v_offset_in().value
        selected_options = self.parts_cb.get_selected_options()
        selected_specifier = self.get_specifier_in().value
        selected_enable = self.get_enable_in().value
        return selected_specifier, selected_options, str(Quantity(offset_str).m_as('cm')), selected_enable  # type: ignore

    def get_changed_locators(self):
        locator_in = self.get_selection_in()
        selected_locators = get_selected_locators(locator_in)
        selected_specifier, selected_options, selected_offset_str, selected_enable = self.get_selected_specifier_options_offset_enable()
        changed_locators: ty.List[VirtualF3Occurrence] = []

        for kl_occ in selected_locators:
            options = [kl_occ.comp_attr[an] for an in ANS_OPTION]
            specifier = kl_occ.comp_attr[AN_LOCATORS_SPECIFIER]
            offset_str = kl_occ.comp_attr[AN_KEY_V_OFFSET]
            enable = bool(kl_occ.comp_attr[AN_LOCATORS_ENABLED])
            if options != selected_options or specifier != selected_specifier or offset_str != selected_offset_str or enable != selected_enable:
                for an, d in zip(ANS_OPTION, selected_options):
                    kl_occ.comp_attr[an] = d
                kl_occ.comp_attr[AN_LOCATORS_SPECIFIER] = selected_specifier
                kl_occ.comp_attr[AN_KEY_V_OFFSET] = selected_offset_str
                kl_occ.comp_attr[AN_LOCATORS_ENABLED] = 'True' if selected_enable else ''
                changed_locators.append(kl_occ)

        return changed_locators

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs) -> None:
        if has_sel_in(self.get_selection_in()):
            self.parts_cb.notify_validate(event_args)
            if not event_args.areInputsValid:
                return
            locator_in = self.get_selection_in()
            specifier_in = self.get_specifier_in()
            selected_locators = get_selected_locators(locator_in)
            selected_specifier, selected_options, selected_offset_str, enable = self.get_selected_specifier_options_offset_enable()
            if '' in selected_options or '' == selected_offset_str:
                event_args.areInputsValid = False
                return
            try:
                self.pi.resolve_specifier(
                    selected_specifier,
                    selected_options[I_ANS_OPTION.CAP_DESC],
                    selected_options[I_ANS_OPTION.STABILIZER_DESC],
                    selected_options[I_ANS_OPTION.SWITCH_DESC],
                    parts_resolver.AlignTo[selected_options[I_ANS_OPTION.KEY_V_ALIGN]])
                specifier_in.tooltip = ''
                # specifier_in.isValueError = False
            except parts_resolver.SpecifierException as e:
                pn = selected_locators[0].comp_attr[AN_LOCATORS_PATTERN_NAME]
                availables = [a for a in e.available_specifiers if pn in a]
                specifier_in.tooltip = 'Available Specifiers:\n' + '\n'.join(availables)
                specifier_in.isValueError = True
                event_args.areInputsValid = False
        else:
            event_args.areInputsValid = False

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        changed_locators = self.get_changed_locators()
        if len(changed_locators) > 0:
            place_key_placeholders(changed_locators)
            con = get_context()
            prepare_key_assembly(self.specs_ops_on_pn, self.pi)
            fill_surrogate()
            con.clear_surrogate()
            con.prepare_parameter_dict.clear()

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        changed_locators = self.get_changed_locators()
        if len(changed_locators) > 0:
            place_key_placeholders(changed_locators)
            pps_part = prepare_key_assembly(self.specs_ops_on_pn, self.pi)
            if len(pps_part) > 0:
                PreparePartsEventHandler(pps_part)
            else:
                fill_surrogate()
        else:
            fill_surrogate()

    def notify_destroy(self, event_args: CommandEventArgs) -> None:
        # Bug workaround of F360. Without the code below, change switch orientation -> cancel button occurs wrong result.
        key_placeholders_occ = get_context().child[CN_INTERNAL].child[CN_KEY_PLACEHOLDERS]
        kd = {n: o.transform for n, o in key_placeholders_occ.child.items()}
        for n, o in key_placeholders_occ.child.items():
            o.transform = kd[n]

        key_locators = get_context().child[CN_INTERNAL].child[CN_KEY_LOCATORS]
        key_locators.light_bulb = self.last_light_bulb


class CheckKeyAssemblyCommandHandler(CommandHandlerBase):
    def __init__(self) -> None:
        super().__init__()
        self.parts_cb: PartsCommandBlock
        self.pi: parts_resolver.PartsInfo

    @property
    def cmd_name(self) -> str:
        return 'Check Key Assembly'

    @property
    def tooltip(self) -> str:
        return 'Assembles a key assembly from a specifier, pattern name, and part descriptions. This command tells you interferences caused by inadequate parts combination. You can use this command to debug your parts data and check a combination which is not usual.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/check_key_assembly'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        con = get_context()
        if con.des.parentDocument.isModified or con.des.parentDocument.isSaved:
            raise BadConditionException("Please use this command on new and unmodified document.")
        self.parts_cb = PartsCommandBlock(self)
        con.des.designType = af.DesignTypes.DirectDesignType
        inl_occ = con.child.get_real(CN_INTERNAL)
        pi_dir = CURRENT_DIR.parent / 'p2ppcb_parts_data_f360'
        self.pi = parts_resolver.PartsInfo(pi_dir / parts_resolver.PARTS_INFO_DIRNAME)
        inl_occ.comp_attr[AN_PARTS_DATA_PATH] = str(pi_dir)
        _ = self.inputs.addStringValueInput(INP_ID_PATTERN_NAME_STR, 'Pattern Name', '')
        _ = self.inputs.addStringValueInput(INP_ID_SPECIFIER_STR, 'Specifier', '')
        self.parts_cb.notify_create(event_args)
        self.parts_cb.show_hide(True)

    def get_specifier_in(self):
        return get_ci(self.inputs, INP_ID_SPECIFIER_STR, ac.StringValueCommandInput)

    def get_pattern_name_in(self):
        return get_ci(self.inputs, INP_ID_PATTERN_NAME_STR, ac.StringValueCommandInput)

    def get_selected_specifier_options_offset(self):
        offset_str = self.parts_cb.get_v_offset_in().value
        selected_options = self.parts_cb.get_selected_options()
        selected_specifier = self.get_specifier_in().value
        return selected_specifier, selected_options, str(Quantity(offset_str).m_as('cm'))  # type: ignore

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs) -> None:
        specifier_in = self.get_specifier_in()
        pattern_name_in = self.get_pattern_name_in()
        specifier_in.tooltip = TOOLTIP_SPECIFIER
        specifier_in.isValueError = False
        pattern_name_in.tooltip = TOOLTIP_PATTERN_NAME
        pattern_name_in.isValueError = False
        for str_in in [specifier_in, pattern_name_in]:
            if len(str_in.value) == 0:
                event_args.areInputsValid = False
                str_in.isValueError = True
        if not event_args.areInputsValid:
            return
        if pattern_name_in.value not in parts_resolver.KEY_AREA_PATTERN_DIC:
            event_args.areInputsValid = False
            pattern_name_in.isValueError = True
            pattern_name_in.tooltip = 'The pattern name is not valid.'
            return
        if pattern_name_in.value not in specifier_in.value:
            event_args.areInputsValid = False
            specifier_in.isValueError = True
            pattern_name_in.isValueError = True
            specifier_in.tooltip = 'Specifier must contain pattern name.'
            return
        self.parts_cb.notify_validate(event_args)
        if not event_args.areInputsValid:
            return
        selected_specifier, selected_options, selected_offset_str = self.get_selected_specifier_options_offset()
        if '' in selected_options or '' == selected_offset_str:
            event_args.areInputsValid = False
            return
        try:
            self.pi.resolve_specifier(
                selected_specifier,
                selected_options[I_ANS_OPTION.CAP_DESC],
                selected_options[I_ANS_OPTION.STABILIZER_DESC],
                selected_options[I_ANS_OPTION.SWITCH_DESC],
                parts_resolver.AlignTo[selected_options[I_ANS_OPTION.KEY_V_ALIGN]])
        except parts_resolver.SpecifierException as e:
            availables = [a for a in e.available_specifiers if pattern_name_in.value in a]
            specifier_in.tooltip = 'Available Specifiers:\n' + '\n'.join(availables)
            specifier_in.isValueError = True
            event_args.areInputsValid = False

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        doc = con.des.parentDocument
        doc.saveAs('P2PPCB Temp', con.app.data.dataProjects[0].rootFolder, 'Temporary file for P2PPCB', '')

        i = 0
        pattern_name = self.get_pattern_name_in().value
        inl_occ = con.child[CN_INTERNAL]
        key_placeholders_occ = inl_occ.child.get_real(CN_KEY_PLACEHOLDERS)
        pp_ka_on_so: ty.Dict[str, PrepareKeyAssemblyParameter] = con.prepare_parameter_dict[PP_KEY_ASSEMBLY_ON_SO]
        pp_ka_on_so.clear()
        specifier, options, offset_str = self.get_selected_specifier_options_offset()
        specifier_options = ' '.join([specifier, ] + options)
        pp = PrepareKeyAssemblyParameter(
            pattern_name,
            specifier,
            options[I_ANS_OPTION.CAP_DESC],
            options[I_ANS_OPTION.STABILIZER_DESC],
            TwoOrientation[options[I_ANS_OPTION.STABILIZER_ORIENTATION]],
            options[I_ANS_OPTION.SWITCH_DESC],
            FourOrientation[options[I_ANS_OPTION.SWITCH_ORIENTATION]],
            parts_resolver.AlignTo[options[I_ANS_OPTION.KEY_V_ALIGN]],
            float(offset_str),
            []
        )
        pp_ka_on_so[specifier_options] = pp
        pp.kps.append(PrepareKeyPlaceholderParameter(i, [''] * 12))
        _ = key_placeholders_occ.child.new_surrogate(key_placeholder_name(i, pattern_name))

        specs_ops_on_pn: SpecsOpsOnPn = {}
        specs_ops_on_pn[pattern_name] = [(specifier, None)]
        pps_part = prepare_key_assembly(specs_ops_on_pn, self.pi)
        PreparePartsEventHandler(pps_part)
