from typing import Any

from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QScrollArea, QVBoxLayout

from console.gui.common.tab import GuiTab


class SettingsTab(GuiTab):
    def __init__(self):
        super().__init__()
        # main_layout = QVBoxLayout(self)
        # scrollable = QScrollArea()
        # scrollable.setWidgetResizable(True)

        # serial_group = QGroupBox()
        # serial_group.setTitle("Serial Tools")

        # main_layout.addWidget(scrollable)

        # port_group = QGroupBox()
        # port_group.setTitle("Manage Connection")
        # port_form = QFormLayout(port_group)
        # self.port_selector = ClickableComboBox()
        # self.port_selector.setItemDelegate(PortComboLabelDelegate())
        # self.port_selector.triggered.connect(self.refresh_ports)
        # self.port_selector.textActivated.connect(self.select_port)
        # port_form.addRow("Port:", self.port_selector)
        # self.dfu_button = QPushButton("Enter DFU Mode")
        # self.dfu_button.clicked.connect(self.enter_dfu)
        # self.disconnect_button = QPushButton("Disconnect")
        # self.disconnect_button.pressed.connect(self.deselect_port)
        # self.dfu_button.setFixedWidth(120)
        # self.disconnect_button.setFixedWidth(120)
        # port_form.addWidget(self.dfu_button)
        # port_form.addWidget(self.disconnect_button)
        # utils_hbox.addWidget(port_group)

        # flash_group = QGroupBox()
        # flash_group.setTitle("STM32 Programmer")
        # flash_form = QFormLayout(flash_group)
        # self.programmer_status = QLabel(
        #     self._PROGRAMMER_STATUS_YES
        #     if self.stm.programmer_present
        #     else self._PROGRAMMER_STATUS_NO
        # )
        # self.usb_selector = ClickableComboBox()
        # self.usb_selector.triggered.connect(self.refresh_usb)
        # self.reset_button = QPushButton("Reset Device")
        # self.reset_button.clicked.connect(self.reset_usb)
        # self.flash_button = QPushButton("Flash Firmware")
        # self.flash_button.clicked.connect(self.flash_usb)
        # flash_form.addRow("Programmer status:", self.programmer_status)
        # flash_form.addRow("Target:", self.usb_selector)
        # flash_form.addWidget(self.reset_button)
        # flash_form.addWidget(self.flash_button)
        # utils_hbox.addWidget(flash_group)
        # self.refresh_timer = QTimer()
        # self.refresh_timer.timeout.connect(self.refresh_all)
        # self.refresh_timer.setInterval(100)
        # self.refresh_timer.start()

        # self._needs_attention = False

        # self.main_layout.addLayout(utils_hbox)