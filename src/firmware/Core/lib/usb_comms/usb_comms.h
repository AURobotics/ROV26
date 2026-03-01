#pragma once

#include <cstdint>

#define SYNC_BYTE 0xFF
#define READY_BYTE 0xAA
#define PAYLOAD_SIZE 30

extern volatile FlowState flow_state;
extern volatile uint8_t data_received;
extern volatile uint8_t rx_buffer[PAYLOAD_SIZE];
extern uint8_t ready_byte;

// start byte, type, message

// Ready message : start byte, type 0
// tuning message: starte byte, size 10, int float float
// sensor message: start, size , yaw pitch roll, 8 thrusters, led, grippers,


struct __attribute__((packed)) RxPacket {
    uint8_t sync_byte;
    uint16_t control_byte; // 4 control bits/ 1 led/ 2 grippers/ 1 toggle : 1 = move & 1 movement: 0
                           // down / 1 up
    float forces[6];
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

enum class Message_Type : uint8_t {
    READY_MESSAGE = 0,
    COMMAND_MESSAGE = 1, // Received from gui to control it
    PARAMETERS_MESSAGE = 2, // received from gui, used to set pid param
    OPERATION_MESSAGE = 3, // received from gui to change operation mode
    SENSOR_MESSAGE = 4 // sent from stm, contains the actuator's state and sensors' data
};

struct __attribute__((packed)) lolo {
    void function();
    int a;
};

void load_tx(TxPacket* tx);
