import typing as ty
import adsk.core as ac
import adsk.fusion as af
from adsk.core import InputChangedEventArgs, CommandEventArgs, CommandCreatedEventArgs, CommandInput
from f360_common import AN_FILL, AN_HOLE, AN_MEV, AN_MF, AN_PLACEHOLDER, AN_TERRITORY, ATTR_GROUP, get_context
from p2ppcb_composer.cmd_common import CommandHandlerBase, get_ci

INP_ID_ENTITY_SEL = 'entity'
INP_ID_ATTR_NAME_DD = 'attrName'
INP_ID_ATTR_VALUE_STR = 'attrValue'

ANS_PART = [AN_HOLE, AN_FILL, AN_MF, AN_MEV, AN_PLACEHOLDER, AN_TERRITORY]


class SetAttributeCommandHandler(CommandHandlerBase):
    def __init__(self):
        super().__init__()

    @property
    def cmd_name(self) -> str:
        return 'Set Attribute'

    @property
    def tooltip(self) -> str:
        return "Sets attributes on part's F3D body. You should be informed about fill/hole MF/MEV method."

    @property
    def resource_folder(self) -> str:
        return 'Resources/set_attribute'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        sel_in = self.inputs.addSelectionInput(INP_ID_ENTITY_SEL, 'Selection', 'Select bodies')
        sel_in.addSelectionFilter('Bodies')
        sel_in.setSelectionLimits(1, 0)

        n_in = self.inputs.addDropDownCommandInput(INP_ID_ATTR_NAME_DD, 'Attr Name', ac.DropDownStyles.TextListDropDownStyle)
        n_in.listItems.add('', True, '', -1)
        for an in ANS_PART:
            n_in.listItems.add(an, False, '', -1)
        self.inputs.addStringValueInput(INP_ID_ATTR_VALUE_STR, 'Value', '')

    def get_entity_in(self) -> ac.SelectionCommandInput:
        return get_ci(self.inputs, INP_ID_ENTITY_SEL, ac.SelectionCommandInput)

    def get_attr_name_in(self) -> ac.DropDownCommandInput:
        return get_ci(self.inputs, INP_ID_ATTR_NAME_DD, ac.DropDownCommandInput)

    def get_attr_value_in(self) -> ac.StringValueCommandInput:
        return get_ci(self.inputs, INP_ID_ATTR_VALUE_STR, ac.StringValueCommandInput)

    def get_inputs(self):
        sel_in = self.get_entity_in()
        bodies: ty.List[af.BRepBody] = []
        for i in range(sel_in.selectionCount):
            selection = sel_in.selection(i)
            body = af.BRepBody.cast(selection.entity)
            bodies.append(body)

        return (bodies, self.get_attr_name_in().selectedItem.name, self.get_attr_value_in().value)

    def notify_input_changed(self, event_args: InputChangedEventArgs, changed_input: CommandInput) -> None:
        bodies, attr_name, _ = self.get_inputs()
        if changed_input.id == INP_ID_ENTITY_SEL:
            name = None
            show_value = None
            for b in bodies:
                if len(b.attributes) == 0:
                    name = ''
                    show_value = ''
                    break
                for a in b.attributes:
                    if a.name in ANS_PART:
                        if name is None:
                            name = a.name
                        elif name != a.name:
                            name = ''
                            show_value = ''
                            break
                    else:
                        continue
                    if show_value is None:
                        show_value = a.value
                    elif show_value != a.value:
                        show_value = ''
                if name == '':
                    break
            name = '' if name is None else name
            for li in self.get_attr_name_in().listItems:
                if li.name == name:
                    li.isSelected = True
                    break
            self.get_attr_value_in().value = '' if show_value is None else show_value
            self.get_entity_in().hasFocus = True
        elif changed_input.id == INP_ID_ATTR_NAME_DD:
            self.get_attr_value_in().value = attr_name

    def notify_execute(self, event_args: CommandEventArgs) -> None:
        con = get_context()
        bodies, attr_name, attr_value = self.get_inputs()
        attrs = con.des.findAttributes(ATTR_GROUP, attr_name)
        for a in attrs:
            if a.value == attr_value:
                a.deleteMe()
        for b in bodies:
            for a in b.attributes:
                a.deleteMe()
            b.attributes.add(ATTR_GROUP, attr_name, attr_value)
