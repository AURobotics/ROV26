// usb_comms.h
#ifndef USB_COMMS_H
#define USB_COMMS_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

#define SYNC_BYTE       0xFF
#define READY_BYTE      0xAA
#define PAYLOAD_SIZE    30

extern volatile FlowState flow_state;
extern volatile uint8_t data_received;
extern volatile uint8_t rx_buffer[PAYLOAD_SIZE];
extern uint8_t ready_byte;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint8_t control_byte;
    float forces[6];
    float gripper_speed;
    uint32_t checksum;
} RxPacket;

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    float motor_speeds[8];
    float gripper_speed;
    float depth;
    float yaw;
    float pitch;
    float roll;
    uint8_t status_byte;
} TxPacket;

typedef enum {
    FLOW_WAITING,
    FLOW_RECEIVING,
    FLOW_SENDING
} FlowState;


void load_tx(TxPacket *tx);

#ifdef __cplusplus
}
#endif
#endif