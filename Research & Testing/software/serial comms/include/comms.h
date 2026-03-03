#pragma once

#include <cstdint>
#include <locale.h>
#include <math.h>

#define SYNC_BYTE 0xFF

// extern volatile FlowState flow_state;
extern volatile uint8_t data_received;
extern volatile uint32_t last_receive_time;
extern volatile struct RxPacket rx_pkt;

// start byte, type, message

// Ready message : start byte, type 0
// tuning message: starte byte, size 10, int float float
// sensor message: start, size , yaw pitch roll, 8 thrusters, led, grippers,

enum class Message_Type : uint8_t
{
    READY_MESSAGE = 0,
    COMMAND_MESSAGE = 1,    // Received from gui to control it
    PARAMETERS_MESSAGE = 2, // received from gui, used to set pid param
    OPERATION_MESSAGE = 3,  // received from gui to change operation mode
    SENSOR_MESSAGE = 4,     // sent from stm, contains the actuator's state and sensors' data
    TUNING_MESSAGE = 5
};

struct __attribute__((packed)) RxPacket
{
    uint8_t sync_byte;
    Message_Type type = Message_Type::COMMAND_MESSAGE;
    uint16_t control_byte; // 4 control bits/ 1 led/ 2 grippers/ 1 toggle : 1 = move & 1 movement: 0
                           // down / 1 up/ 1 disable safety circuit
    float forces[6];
    //  Force on X
    //  Force on Y
    //  Force on Z
    //  Torque on pitch
    //  Torque on roll
    //  Torque on yaw
};

struct __attribute__((packed)) Parameter_Msg
{
    uint8_t sync_byte = SYNC_BYTE;
    Message_Type type = Message_Type::PARAMETERS_MESSAGE;
    float Kp, kd, ki;
};

struct __attribute__((packed)) Operation_Msg
{
    uint8_t sync_byte = SYNC_BYTE;
    Message_Type type = Message_Type::OPERATION_MESSAGE;
    uint8_t time;
    float angle, rate; // le7ad ma mina yrod 3alaya
};

struct __attribute__((packed)) Tuning_Msg
{
    uint8_t sync_byte = SYNC_BYTE;
    Message_Type type = Message_Type::TUNING_MESSAGE;
    uint8_t axis;
};

struct __attribute__((packed)) Ready_Msg
{
    uint8_t sync_byte = SYNC_BYTE;
    Message_Type type = Message_Type::READY_MESSAGE;
};

struct __attribute__((packed)) TxPacket
{
    uint8_t sync_byte = SYNC_BYTE;
    Message_Type type = Message_Type::SENSOR_MESSAGE;
    uint8_t status{}; // led, 2 grippers, 2 bits for switches
    float depth{};
    float yaw{};
    float pitch{};
    float roll{};
    float motor_speeds[8]{};
};
#define MAX2(a, b) ((a) > (b) ? (a) : (b))
#define MAX3(a, b, c) MAX2(MAX2(a, b), c)
constexpr int PAYLOAD_SIZE = MAX3(sizeof(RxPacket), sizeof(Parameter_Msg), sizeof(Operation_Msg));
extern volatile uint8_t rx_buffer[PAYLOAD_SIZE];