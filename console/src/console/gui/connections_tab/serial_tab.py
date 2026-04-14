from PySide6.QtGui import QFont, QHideEvent, QShowEvent
from PySide6.QtWidgets import (
    QGroupBox,
    QStyle,
    QStyledItemDelegate,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFormLayout,
)
from PySide6.QtCore import QSize, Qt, Slot
from string import Template
from console.comms.rov.stm32 import Stm32
from core.concurrent.callback_worker import CallbackWorker
from hal.serial.serial_device import list_ports


class PortComboLabelDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()

        sub_text = index.data(Qt.ItemDataRole.DisplayRole)  # device name
        main_text = index.data(Qt.ItemDataRole.UserRole)  # hardware description

        option.widget.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, option, painter
        )

        main_font = QFont(option.font)
        main_font.setBold(True)
        painter.setFont(main_font)

        rect = option.rect
        painter.drawText(
            rect.adjusted(5, 2, 0, -rect.height() / 2),
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            main_text,
        )

        if sub_text:
            sub_font = QFont(option.font)
            sub_font.setPointSize(option.font.pointSize() - 2)
            painter.setFont(sub_font)
            painter.setPen(Qt.GlobalColor.gray)
            painter.drawText(
                rect.adjusted(5, rect.height() / 2, 0, -2),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                sub_text,
            )

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 45)


class SerialTab(QWidget):
    _DISCONNECTED_STATUS = "Not connected to STM32"
    _DISCONNECTED_HINT = "Please choose a serial device below"
    _CONNECTED_STATUS = Template("Connected to $name")
    _CONNECTED_HINT = Template("Port: $port")

    def __init__(self, stm: Stm32):
        super().__init__()
        self.stm = stm

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addStretch()
        self.status_label = QLabel(self._DISCONNECTED_STATUS)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.main_layout.addWidget(self.status_label)
        self.hint_label = QLabel(self._DISCONNECTED_HINT)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setStyleSheet("font-size: 12px;")
        self.main_layout.addWidget(self.hint_label)
        self.main_layout.addStretch()

        utils_hbox = QHBoxLayout()
        port_group = QGroupBox()
        port_group.setTitle("Manage Connection")
        port_form = QFormLayout(port_group)
        self.port_selector = QComboBox()
        self.port_selector.setItemDelegate(PortComboLabelDelegate())
        self.port_selector.activated.connect(self.refresh_ports)
        self.port_selector.textActivated.connect(self.select_port)
        port_form.addRow("Port:", self.port_selector)
        self.dfu_button = QPushButton("Enter DFU Mode")
        self.dfu_button.clicked.connect(self.stm.enter_dfu)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.pressed.connect(self.deselect_port)
        self.dfu_button.setFixedWidth(120)
        self.disconnect_button.setFixedWidth(120)
        port_form.addWidget(self.dfu_button)
        port_form.addWidget(self.disconnect_button)
        utils_hbox.addWidget(port_group)

        flash_group = QGroupBox()
        flash_group.setTitle("STM32 Programmer")
        flash_form = QFormLayout(flash_group)
        self.usb_selector = QComboBox()
        self.usb_selector.activated.connect(self.refresh_usb)
        self.reset_button = QPushButton("Reset Device")
        self.flash_button = QPushButton("Flash Firmware")
        flash_form.addRow("Target:", self.usb_selector)
        flash_form.addWidget(self.reset_button)
        flash_form.addWidget(self.flash_button)
        utils_hbox.addWidget(flash_group)

        self.main_layout.addLayout(utils_hbox)

        self.refresh_usb()

    @Slot(str)
    def select_port(self, port: str) -> None:
        if self.stm.port == port:
            return
        try:
            worker = CallbackWorker(
                lambda: self.stm.connect(port), self.on_port_selection_change
            )
            worker.run()
        except:
            pass

    @Slot()
    def deselect_port(self) -> None:
        if not self.stm.port:
            return
        try:
            worker = CallbackWorker(self.stm.disconnect, self.on_port_selection_change)
            worker.run()
        except:
            pass

    @Slot()
    def on_port_selection_change(self) -> None:
        if self.stm.port:
            self.port_selector.setCurrentText(self.stm.port)
            self.status_label.setText(
                self._CONNECTED_STATUS.safe_substitute(name=self.stm.name)
            )
            self.hint_label.setText(
                self._CONNECTED_HINT.safe_substitute(port=self.stm.port)
            )
        else:
            self.status_label.setText(self._DISCONNECTED_STATUS)
            self.hint_label.setText(self._DISCONNECTED_HINT)
            self.port_selector.setCurrentIndex(-1)

    @Slot()
    def refresh_usb(self) -> None:
        devices = self.stm.programmable_devices
        if not self.stm.programmer_present or not devices:
            self.usb_selector.clear()
            self.reset_button.setEnabled(False)
            self.flash_button.setEnabled(False)
            return
        selected = self.usb_selector.currentText()
        self.usb_selector.clear()
        for port, description in devices:
            self.usb_selector.addItem(port)
            last_idx = self.usb_selector.count() - 1
            self.port_selector.setItemData(
                last_idx, description, Qt.ItemDataRole.UserRole
            )
            if selected == port:
                self.usb_selector.setCurrentIndex(last_idx)

        if self.usb_selector.currentIndex() == -1:
            self.usb_selector.setCurrentIndex(0)

    @Slot()
    def refresh_ports(self) -> None:
        self.port_selector.clear()

        for p in list_ports():
            self.port_selector.addItem(p.device)
            last_idx = self.port_selector.count() - 1
            self.port_selector.setItemData(
                last_idx, p.description, Qt.ItemDataRole.UserRole
            )

        connected = self.stm.port is not None
        self.dfu_button.setEnabled(connected)
        self.disconnect_button.setEnabled(connected)
        if not connected:
            self.port_selector.setCurrentIndex(-1)
            return
        for i in range(self.port_selector.count()):
            if self.stm.port == self.port_selector.itemText(i):
                self.port_selector.setCurrentIndex(i)
                return

        self.port_selector.setCurrentIndex(-1)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh_ports()
        return

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self.port_selector.clear()
        return
