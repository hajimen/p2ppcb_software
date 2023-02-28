import typing as ty
import re
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput
from f360_common import get_context
from p2ppcb_composer.cmd_common import CommandHandlerBase


INP_ID_COMPONENT_BOOL = 'selectComponent'
INP_ID_STR_STR = 'regexStr'
INP_ID_HIT_STR = 'hitCount'
INP_ID_SEARCH_BOOL = 'search'


class RegexSelectCommandHandler(CommandHandlerBase):
    def __init__(self) -> None:
        super().__init__()
        self.to_select_cache = []
        self.str_cache = ''
        self.comp_cache = False

    @property
    def cmd_name(self) -> str:
        return 'Regex Select'

    @property
    def tooltip(self) -> str:
        return 'Makes a selection set of bRepBodies/occurrences by regex of full path. The path separator before occurrences is +, before bRepBodies is ?.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/regex_selector'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        self.to_select_cache = []
        self.str_cache = ''
        self.comp_cache = False

        comp_in = self.inputs.addBoolValueInput(INP_ID_COMPONENT_BOOL, 'Select Components', True)
        comp_in.tooltip = 'Select Components. Otherwise select bodies.'
        comp_in.value = False

        _ = self.inputs.addStringValueInput(INP_ID_STR_STR, 'Regex String', '')

        hit_in = self.inputs.addStringValueInput(INP_ID_HIT_STR, 'Hit Count', '-')
        hit_in.isReadOnly = True

        search_in = self.inputs.addBoolValueInput(INP_ID_SEARCH_BOOL, 'Search', False)
        search_in.tooltip = 'Click to search.'
        search_in.value = False

    def get_comp_in(self):
        return ac.BoolValueCommandInput.cast(self.inputs.itemById(INP_ID_COMPONENT_BOOL))

    def get_str_in(self):
        return ac.StringValueCommandInput.cast(self.inputs.itemById(INP_ID_STR_STR))

    def get_hit_in(self):
        return ac.StringValueCommandInput.cast(self.inputs.itemById(INP_ID_HIT_STR))

    def get_search_in(self):
        return ac.BoolValueCommandInput.cast(self.inputs.itemById(INP_ID_SEARCH_BOOL))

    def notify_validate(self, event_args: ac.ValidateInputsEventArgs):
        if len(self.get_str_in().value) == 0 or not self.get_search_in().value:
            event_args.areInputsValid = False

    def cache_ok(self):
        rs = self.get_str_in().value
        select_comp = self.get_comp_in().value
        return rs == self.str_cache and select_comp == self.comp_cache

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        if not self.cache_ok():
            if changed_input.id != INP_ID_SEARCH_BOOL and self.get_search_in().value:
                self.get_search_in().value = False
                get_context().ui.activeSelections.clear()

    def search_rec(self, m: re.Pattern, occ: ty.Optional[af.Occurrence], select_comp: bool):
        ret = []
        comp = occ.component if occ is not None else get_context().comp
        fpn = '' if occ is None else occ.fullPathName
        if not select_comp:
            for b in comp.bRepBodies:
                if m.fullmatch(fpn + '?' + b.name) is not None:
                    ret.append(b.createForAssemblyContext(occ) if occ is not None else b)
        for o in comp.occurrences if occ is None else [ro.createForAssemblyContext(occ) for ro in comp.occurrences]:
            fpn = o.fullPathName
            if select_comp:
                if m.fullmatch(fpn) is not None:
                    ret.append(o)
            ret.extend(self.search_rec(m, o, select_comp))
        return ret

    def search(self):
        if self.cache_ok():
            return self.to_select_cache
        rs = self.get_str_in().value
        select_comp = self.get_comp_in().value
        matcher = re.compile(self.get_str_in().value)
        to_select = self.search_rec(matcher, None, select_comp)
        self.str_cache = rs
        self.to_select_cache = to_select
        self.comp_cache = select_comp
        return to_select

    def execute_common(self):
        con = get_context()
        con.ui.activeSelections.clear()
        to_select = self.search()
        for ent in to_select:
            con.ui.activeSelections.add(ent)
        self.get_hit_in().value = str(len(to_select))

    def notify_execute_preview(self, event_args: CommandEventArgs) -> None:
        self.execute_common()

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        self.execute_common()
        get_context().app.executeTextCommand('NuComponents.CreateSelectionGroupCmd')
