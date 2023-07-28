import platform
from adsk.core import CommandCreatedEventArgs
from f360_common import get_context
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
        msg = 'P2PPCB Composer F360\n\n' + \
            f'Version: {p2ppcb_composer.__version__}\n' + \
            f'CPU arch: {platform.machine()}\n' + \
            f'OS: {platform.system()}\n' + \
            'License: MIT license\n' + \
            'From: DecentKeyboards'
        get_context().ui.messageBox(msg)
