#ifndef USB_COMMS_H
#define USB_COMMS_H
#ifdef __cplusplus
extern "C" {
#endif
#include <stdint.h>

#define SYNC_BYTE 0xFF
#define READY_BYTE 0xAA

// start byte, type, message

// Ready message : start byte, type 0
// tuning message: starte byte, size 10, int float float
// sensor message: start, size , yaw pitch roll, 8 thrusters, led, grippers,


enum Message_Type {
    READY_MESSAGE = 0,
    COMMAND_MESSAGE = 1, // Received from gui to control it
    PARAMETERS_MESSAGE = 2, // received from gui, used to set pid param
    OPERATION_MESSAGE = 3, // received from gui to change operation mode
    SENSOR_MESSAGE = 4, // sent from stm, contains the actuator's state and sensors' data
    TUNING_MESSAGE = 5,
    CONTROLLER_RESPONSE = 6,
    DFU_mode = 7
};

enum Control_byte_bit_mask {
    CONTROL = 0,
    LED = 4,
    DCVS = 5,
    ROT_GRP_EN = 7,
    ROT_GRP_DIR = 8,
};

inline uint16_t word_read(const uint16_t word, const int mask) {
    return word & 1 << (15 - mask);
}

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t type;
    uint16_t control_byte; // 4 control bits/ 1 led/ 2 grippers/ 1 toggle : 1 = move & 1 movement: 0
                           // down , 1 up
    float forces[6];
} Command_msg;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t type;
    uint8_t axis; // 0 depth, 1 pitch, 2 roll, 3 yaw
    uint8_t pid_type;
    float Kp, kd, ki;
} Parameter_Msg;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t type;
    uint8_t operation_mode; // 0 normal operation, 1 testing and tuning operation
} Operation_Mode_Msg;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t type;
    uint8_t axis;
} Tuning_Msg;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t type;
} Ready_msg;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t type;
    int16_t timestamp;
    float angle;
    float angle_rate;
} Step_response_msg;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t type;
    uint8_t status; // led, 2 grippers, 2 bits for limit switches
    float depth;
    float yaw;
    float pitch;
    float roll;
    float motor_speeds[8];
} Sensor_msg;


void load_tx(Sensor_msg* tx);

#ifdef __cplusplus
}
#endif
#endif // USB_COMMS_H
