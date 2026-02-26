import serial
import serial.tools.list_ports
import time
import threading


class STM32:
    def __init__(self, baudrate: int):
        self._serial = serial.Serial(port=None, baudrate=baudrate)
        self._connected = False
        self._connection_in_progress = False
        self.baudrate = baudrate
        self._port = None
        self._stm_port = None

    @property
    def connected(self):
        return self._connected

    @property
    def available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value  # Set the private attribute, not self.port!

    @property
    def incoming(self):
        if self.connected:
            return self._serial.in_waiting
        else:
            return self.connected

    def clean(self):
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

    def connect(self, port: str):
        self._serial.close()
        self._connection_in_progress = True

        def _connection_thread():
            try:
                # ...handelling the rfc2217 port connection missing
                self._serial.port = port
                self._serial.open()
                self._connected = True
                time.sleep(0.1)  # Small delay for Arduino to boot
                self.clean()
            except Exception as e:
                print(e)
                self._serial.port = None
            finally:
                self._connection_in_progress = False
                if not self.connected:
                    self.connect(port)

        connection_thread = threading.Thread(target=_connection_thread)
        connection_thread.start()

    def disconnect(self):
        if not self.connected:  # disconnect only when connected
            return
        self._serial.close()
        self._serial.port = None
        self._connected = False

    def send(self, data):
        if self.connected:
            self._serial.write(data)

    @property
    def recieve(self, size=1):
        if self.connected and self.incoming:
            buf = self._serial.read(size)
            if buf is None:
                self.clean()
            if len(buf) > 0:
                return buf

    def reset_connection(self):
        if self.connected and not self.incoming:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            self.disconnect()

            self._serial = serial.Serial(port=None, baudrate=self.baudrate)

            if self.port is not None:
                self.connect(self.port)

