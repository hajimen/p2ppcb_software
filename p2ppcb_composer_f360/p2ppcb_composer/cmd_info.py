from adsk.core import CommandCreatedEventArgs
from f360_common import get_context, get_platform_tag
from p2ppcb_composer.cmd_common import CommandHandlerBase


class InfoCommandHandler(CommandHandlerBase):
    def __init__(self) -> None:
        super().__init__()
        self.require_cn_internal = False
        self.require_cn_key_locators = False

    @property
    def cmd_name(self) -> str:
        return 'Information'

    @property
    def tooltip(self) -> str:
        return 'Information about this add-in.'

    @property
    def resource_folder(self) -> str:
        return 'Resources/info'

    def notify_create(self, event_args: CommandCreatedEventArgs):
        import p2ppcb_composer
        tag = get_platform_tag()
        con = get_context()
        msg = f'Version: {p2ppcb_composer.__version__}\n' + \
            f'Platform tag: {tag}\n' + \
            'License: MIT license\n' + \
            'From: DecentKeyboards'
        con.ui.messageBox(msg)
