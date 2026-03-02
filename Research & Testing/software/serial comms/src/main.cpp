#include <Arduino.h>
#include <comms.h>
#include <cmath>
#include <cstdio>
#include <optional>

Ready_Msg ready_msg;

TxPacket dummy = {
    .sync_byte = 0xFF,
    .type = Message_Type::SENSOR_MESSAGE,
    .status = 0x01,
    .depth = 10.5f,
    .yaw = 45.0f,
    .pitch = -15.0f,
    .roll = 5.0f,
    .motor_speeds = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f}};

volatile uint32_t last_send_time = 0;
volatile Message_Type detected_rx;
volatile bool synced = false;

void setup()
{
  Serial.begin(115200);
}

void loop() {
  // --- ASYNCHRONOUS SENDING (Independent of receiving) ---
  if (millis() - last_send_time >= 50) {
    last_send_time = millis();
    Serial.write(reinterpret_cast<uint8_t *>(&dummy), sizeof(TxPacket));
  }

  // Only send Ready_Msg if we aren't currently mid-packet
  if (!synced) {
     Serial.write((uint8_t *)&ready_msg, sizeof(Ready_Msg));
  }

  // --- ASYNCHRONOUS RECEIVING ---
  while (Serial.available() > 0) {
    // 1. Check for timeout (if Python stopped sending mid-stream)
    if (synced && (millis() - last_receive_time > 20)) {
      synced = false;
      detected_rx = Message_Type::READY_MESSAGE;
    }

    // 2. Look for Sync
    if (!synced) {
      if (Serial.read() == SYNC_BYTE) {
        synced = true;
        last_receive_time = millis();
        detected_rx = Message_Type::READY_MESSAGE;
      }
      continue;
    }

    // 3. Identify Message Type
    if (detected_rx == Message_Type::READY_MESSAGE) {
      if (Serial.available() > 0) {
        detected_rx = static_cast<Message_Type>(Serial.read());
        last_receive_time = millis();
      } else {
        break; // Wait for the type byte to arrive
      }
    }

    // 4. Handle Payload
    size_t target_size = (detected_rx == Message_Type::COMMAND_MESSAGE) ? sizeof(RxPacket) : 0;
    // (Add other types here)

    if (target_size > 0) {
      // Check if the REMAINING bytes are here (Total - 2 we already read)
      if (Serial.available() >= (target_size - 2)) {
        // Read the rest. Start writing into the buffer at index 2
        Serial.readBytes((char *)rx_buffer + 2, target_size - 2);
        
        // Success! Reset for next time
        synced = false;
        detected_rx = Message_Type::READY_MESSAGE;
      } else {
        // NOT ENOUGH DATA YET. 
        // Important: 'break' so we can go send sensor data while we wait!
        break; 
      }
    }
  }
}