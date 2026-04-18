from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox

class AutoControlInput(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._outer_layout = QVBoxLayout(self)

        self._form = QFormLayout()

        self._pitch_input = QLineEdit()
        self._yaw_input = QLineEdit()
        self._roll_input = QLineEdit()
        self._depth_input = QLineEdit()

        for field in [self._pitch_input, self._yaw_input, self._roll_input, self._depth_input]:
            field.setClearButtonEnabled(True)
            field.setPlaceholderText('target')

        self._form.addRow('pitch:', self._pitch_input)
        self._form.addRow('yaw:', self._yaw_input)
        self._form.addRow('roll:', self._roll_input)
        self._form.addRow('depth:', self._depth_input)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self.confirmInput)
        self._buttons.rejected.connect(self.clearInput)

        self._outer_layout.addLayout(self._form)
        self._outer_layout.addWidget(self._buttons)

    def confirmInput(self):
        ...

    def clearInput(self):
        for field in [self._pitch_input, self._yaw_input, self._roll_input, self._depth_input]:
            field.clear()