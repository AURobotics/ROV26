#include <Arduino.h>
#include <comms.h>
#include <cmath>
#include <cstdio>
#include <optional>

Ready_Msg ready_msg;

// Sensor data packet sent back to Python

volatile uint32_t last_send_time = 0;
volatile uint32_t last_ready_time = 0;
volatile Message_Type detected_rx = Message_Type::READY_MESSAGE;
volatile bool synced = false;
// last_receive_time, rx_buffer, rx_pkt, data_received defined in comms.cpp

void process_command()
{
  TxPacket tx_packet = {
      .sync_byte = 0xFF,
      .type = Message_Type::SENSOR_MESSAGE,
      .status = 0x00,
      .depth = (random(0, 10001) / 5000.0) - 1.0,
      .yaw = (random(0, 10001) / 5000.0) - 1.0,
      .pitch = (random(0, 10001) / 5000.0) - 1.0,
      .roll = (random(0, 10001) / 5000.0) - 1.0,
      .motor_speeds = {(random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0}};

  // Parse the received bytes into an RxPacket
  RxPacket *cmd = (RxPacket *)rx_buffer;

  // Echo forces[0..5] into motor_speeds[0..5] so Python can see controller input
  // (Replace this with real thruster allocation later)
  for (int i = 0; i < 6; i++)
  {
    tx_packet.motor_speeds[i] = cmd->forces[i];
  }
  tx_packet.motor_speeds[6] = 0.0f;
  tx_packet.motor_speeds[7] = 0.0f;

  // Mirror LED bit from control_byte bit 0 into status bit 2
  uint8_t led = (cmd->control_byte >> 0) & 1;
  tx_packet.status = (tx_packet.status & ~(1 << 2)) | (led << 2);

  // TODO: replace with real sensor readings when IMU/depth sensor is connected
  // tx_packet.depth = ms5611::getDepth();
  // vec_3 euler = bno055::get_euler_angles();
  // tx_packet.yaw   = euler.z();
  // tx_packet.pitch = euler.y();
  // tx_packet.roll  = euler.x();
}

void setup()
{
  Serial.begin(115200);
}

void loop()
{
  TxPacket tx_packet = {
      .sync_byte = 0xFF,
      .type = Message_Type::SENSOR_MESSAGE,
      .status = 0x00,
      .depth = (random(0, 10001) / 5000.0) - 1.0,
      .yaw = (random(0, 10001) / 5000.0) - 1.0,
      .pitch = (random(0, 10001) / 5000.0) - 1.0,
      .roll = (random(0, 10001) / 5000.0) - 1.0,
      .motor_speeds = {(random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0, (random(0, 10001) / 5000.0) - 1.0}};

  // --- SEND SENSOR_MESSAGE every 50ms (20Hz) ---
  if (millis() - last_send_time >= 50)
  {
    last_send_time = millis();
    Serial.write(reinterpret_cast<uint8_t *>(&tx_packet), sizeof(TxPacket));
  }

  // --- SEND READY_MESSAGE every 500ms ---
  if (!synced && millis() - last_ready_time >= 500)
  {
    last_ready_time = millis();
    Serial.write((uint8_t *)&ready_msg, sizeof(Ready_Msg));
  }

  // --- RECEIVE COMMAND_MESSAGE ---
  while (Serial.available() > 0)
  {

    // 1. Timeout check — reset if Python stopped mid-packet
    if (synced && (millis() - last_receive_time > 20))
    {
      synced = false;
      detected_rx = Message_Type::READY_MESSAGE;
    }

    // 2. Hunt for sync byte (0xFF)
    if (!synced)
    {
      if (Serial.read() == SYNC_BYTE)
      {
        synced = true;
        last_receive_time = millis();
        detected_rx = Message_Type::READY_MESSAGE;
      }
      continue;
    }

    // 3. Read message type byte
    if (detected_rx == Message_Type::READY_MESSAGE)
    {
      if (Serial.available() > 0)
      {
        detected_rx = static_cast<Message_Type>(Serial.read());
        last_receive_time = millis();
      }
      else
      {
        break;
      }
    }

    // 4. Handle payload
    size_t target_size = (detected_rx == Message_Type::COMMAND_MESSAGE) ? sizeof(RxPacket) : 0;

    if (target_size > 0)
    {
      if (Serial.available() >= (int)(target_size - 2))
      {
        rx_buffer[0] = SYNC_BYTE;
        rx_buffer[1] = (uint8_t)detected_rx;
        Serial.readBytes((char *)rx_buffer + 2, target_size - 2);

        // Process the received command and update tx_packet
        process_command();

        synced = false;
        detected_rx = Message_Type::READY_MESSAGE;
      }
      else
      {
        break;
      }
    }
    else
    {
      synced = false;
      detected_rx = Message_Type::READY_MESSAGE;
      break;
    }
  }
}