#include <Arduino.h>
#include <comms.h>
#include <cmath>
#include <cstdio>
#include <optional>

Ready_Msg ready_msg;

double normalize_angle(double angle)
{
  angle = fmod(angle, 360.0);
  if (angle > 180.0)
    angle -= 360.0;
  else if (angle < 180.0)
    angle += 360.0;

  return angle;
}

double angle_diff(double setpoint, double current)
{
  double diff = setpoint - current;
  return normalize_angle(diff);
}

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
  Serial.begin(9600);
}

void loop()
{

  RxPacket rx_pkt;
  TxPacket tx_pkt;

  last_receive_time = millis();

  while (Serial.available())
  {
    if (millis() - last_receive_time < 30)
    {
      while (Serial.available())
        Serial.read();
      detected_rx = Message_Type::READY_MESSAGE;
      break;
    }
    last_receive_time = millis();
    uint8_t next = (uint8_t)Serial.read();
    if (next == SYNC_BYTE)
    {
      synced = true;
      continue;
    }
    else if (synced == false)
    {
      continue;
    }
    if (detected_rx == Message_Type::READY_MESSAGE)
    {
      Message_Type possible_type = static_cast<Message_Type>(next);
      if (possible_type == Message_Type::COMMAND_MESSAGE || possible_type == Message_Type::OPERATION_MESSAGE || possible_type == Message_Type::PARAMETERS_MESSAGE)
      {
        detected_rx = possible_type;
        continue;
      }
      else
      {
        last_receive_time = 0; // flag to empty buffer
        break;
      }
    }

    if (detected_rx == Message_Type::COMMAND_MESSAGE)
    {
      if (Serial.available() + 2 < sizeof(RxPacket))
        continue;
      else
        Serial.readBytes((char*)rx_buffer, sizeof(RxPacket));
    }
    else if (detected_rx == Message_Type::OPERATION_MESSAGE)
    {
      if (Serial.available() + 2 < sizeof(Operation_Msg))
        continue;
      else
        Serial.readBytes((char*)rx_buffer, sizeof(Operation_Msg));
    }
    else if (detected_rx == Message_Type::PARAMETERS_MESSAGE)
    {
      if (Serial.available() + 2 < sizeof(Parameter_Msg))
        continue;
      else
        Serial.readBytes((char*)rx_buffer, sizeof(Parameter_Msg));
    }
  }

  if (millis() - last_send_time >= 50)
  {
    last_send_time = millis();
    Serial.write(reinterpret_cast<uint8_t *>(&dummy), sizeof(TxPacket));
  }

  Serial.write((uint8_t *)&ready_msg, sizeof(Ready_Msg));
}