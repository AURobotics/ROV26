from typing import Any

from console.gui.common.tab import GuiTab


class SettingsTab(GuiTab):
    def __init__(self):
        super().__init__()

    def on_settings_changed(self, key: str, value: Any) -> None: ...
