#pragma once

#include <cstdint>

#define SYNC_BYTE 0xFF
#define READY_BYTE 0xAA
#define PAYLOAD_SIZE 30


// start byte, type, message

// Ready message : start byte, type 0
// tuning message: starte byte, size 10, int float float
// sensor message: start, size , yaw pitch roll, 8 thrusters, led, grippers,


enum class Message_Type : uint8_t {
    READY_MESSAGE = 0,
    COMMAND_MESSAGE = 1, // Received from gui to control it
    PARAMETERS_MESSAGE = 2, // received from gui, used to set pid param
    OPERATION_MESSAGE = 3, // received from gui to change operation mode
    SENSOR_MESSAGE = 4, // sent from stm, contains the actuator's state and sensors' data
    TUNING_MESSAGE = 5,
    CONTROLLER_RESPONSE = 6
};


struct __attribute__((packed)) RxPacket {
    uint8_t sync_byte;
    uint16_t control_byte; // 4 control bits/ 1 led/ 2 grippers/ 1 toggle : 1 = move & 1 movement: 0
                           // down , 1 up / 1 bit enable or disable water sensors / 1 bit enable
                           // disable limit switches
    float forces[6];
};

struct __attribute__((packed)) Parameter_Msg {
    uint8_t sync_byte = 0xFF;
    Message_Type type = Message_Type::PARAMETERS_MESSAGE;
    uint8_t axis{}; // 0 depth, 1 pitch, 2 roll, 3 yaw
    float Kp{}, kd{}, ki{};
};

struct __attribute__((packed)) Operation_Mode_Msg {
    uint8_t sync_byte = 0xFF;
    Message_Type type = Message_Type::OPERATION_MESSAGE;
    uint8_t operation_mode{}; // 0 normal operation, 1 testing and tuning operation
};

struct __attribute__((packed)) Tuning_Msg {
    uint8_t sync_byte = 0xFF;
    Message_Type type = Message_Type::TUNING_MESSAGE;
    uint8_t axis{};
};

struct __attribute__((packed)) Ready_Msg {
    uint8_t sync_byte = 0xFF;
    Message_Type type = Message_Type::READY_MESSAGE;
};

struct __attribute__((packed)) Controller_response_msg {
    uint8_t sync_byte = 0xFF;
    Message_Type type = Message_Type::CONTROLLER_RESPONSE;
    int16_t timestamp{};
    float angle{};
    float angle_rate{};
};

struct __attribute__((packed)) TxPacket {
    uint8_t sync_byte = 10;
    uint8_t type{};
    uint8_t status{}; // led, 2 grippers, 2 bits for switches
    float depth{};
    float yaw{};
    float pitch{};
    float roll{};
    float motor_speeds[8]{};
};

inline uint32_t last_receive_time{};
inline RxPacket rx_pkt{};
inline uint8_t data_received{};
inline Operation_Mode_Msg op_pkt{};
inline Parameter_Msg param_msg{};


void load_tx(TxPacket* tx);
