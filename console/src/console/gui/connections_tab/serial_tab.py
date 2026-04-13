from PySide6.QtGui import QFont
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

from console.comms.stm32 import Stm32
from core.concurrent.callback_worker import CallbackWorker
from hal.serial.serial_device import list_ports


class PortComboLabelDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()

        main_text = index.data(Qt.ItemDataRole.DisplayRole)
        sub_text = index.data(Qt.ItemDataRole.UserRole)

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
    def __init__(self, stm: Stm32):
        super().__init__()
        self.stm = stm

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)

        self.status_label = QLabel("Connected to STM32")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.main_layout.addWidget(self.status_label)

        utils_hbox = QHBoxLayout()
        port_group = QGroupBox()
        port_group.setTitle("Manage Connection")
        port_form = QFormLayout(port_group)
        self.port_selector = QComboBox()
        self.port_selector.setItemDelegate(PortComboLabelDelegate())
        self.port_selector.textActivated.connect(self.select_port)
        port_form.addRow("Port:", self.port_selector)
        self.dfu_btn = QPushButton("Enter DFU Mode")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.pressed.connect(self.deselect_port)
        self.dfu_btn.setFixedWidth(120)
        self.disconnect_button.setFixedWidth(120)
        port_form.addWidget(self.dfu_btn)
        port_form.addWidget(self.disconnect_button)
        utils_hbox.addWidget(port_group)

        flash_group = QGroupBox()
        flash_group.setTitle("STM32 Programmer")
        flash_form = QFormLayout(flash_group)
        self.usb_selector = QComboBox()
        self.reset_btn = QPushButton("Reset Device")
        self.flash_btn = QPushButton("Flash Firmware")
        flash_form.addRow("Target:", self.usb_selector)
        flash_form.addWidget(self.reset_btn)
        flash_form.addWidget(self.flash_btn)
        utils_hbox.addWidget(flash_group)

        self.main_layout.addLayout(utils_hbox)

        self.refresh_ports()

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
            worker = CallbackWorker(
                self.stm.disconnect, self.on_port_selection_change
            )
            worker.run()
        except:
            pass

    def on_port_selection_change(self) -> None:
        if self.stm.port:
            self.port_selector.setCurrentText(self.stm.port)
        else:
            self.port_selector.setCurrentIndex(-1)

    def refresh_ports(self):
        self.port_selector.clear()

        for p in list_ports():
            self.port_selector.addItem(p.device)
            last_idx = self.port_selector.count() - 1
            self.port_selector.setItemData(
                last_idx, p.description, Qt.ItemDataRole.UserRole
            )

        self.port_selector.setCurrentIndex(-1) # TODO: handle port already selected
