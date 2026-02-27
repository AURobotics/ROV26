from serial import Serial
import struct

FORMAT = '<BH6f'
PACKET_SIZE = struct.calcsize(FORMAT)  # 27 bytes
HEADER = 255
MSG_ID = 19

esp = Serial('COM27', baudrate=3600, timeout=1)

while True:
    # --- SEND ---
    payload = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    packet = struct.pack(FORMAT, HEADER, MSG_ID, *payload)
    esp.write(packet)

    # --- RECEIVE ---
    raw = esp.read(PACKET_SIZE)
    if len(raw) == PACKET_SIZE:
        values = struct.unpack(FORMAT, raw)
        header  = values[0]
        msg_id  = values[1]
        floats  = list(values[2:])
        print(f"Header: {header} | MSG_ID: {msg_id} | Values: {floats}")
    else:
        print(f"Incomplete packet: got {len(raw)} bytes, expected {PACKET_SIZE}")