from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QWidget,
    QLineEdit,
)

from console.comms.manager import AutomaticControlData, CommunicationManager


class FormEntry(QWidget):
    def __init__(self, entry_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.entry_name = entry_name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.checkbox = QCheckBox()
        self.line_edit = QLineEdit()
        self.line_edit.setValidator(QDoubleValidator())
        self.line_edit.setPlaceholderText("target")
        self.line_edit.setClearButtonEnabled(True)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.line_edit)
        self.setLayout(layout)


class AutoControlInput(QWidget):
    def __init__(
        self,
        comms: CommunicationManager,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        form = QFormLayout(self)
        self.comms = comms

        field_names = ["yaw", "pitch", "roll", "depth"]
        self.fields = [FormEntry(f) for f in field_names]
        for field in self.fields:
            field.line_edit.editingFinished.connect(self.update_control_data)
            field.checkbox.clicked.connect(self.update_control_data)
            form.addRow(field.entry_name.capitalize() + ":", field)

    def update_control_data(self):
        new_control_data = AutomaticControlData(
            **{
                field.entry_name: float(field.line_edit.text())
                if field.line_edit.hasAcceptableInput()
                else None
                for field in self.fields
            }
        )
        self.comms.set_automatic_control(new_control_data)
