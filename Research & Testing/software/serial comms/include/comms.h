// usb_comms.h

// ready message: 0xFF 0x01 0xAA <- they send this to us
// status message: 0xFF SIZE TxPacket <- they send every 40ms

// 0xFF RxPacket <- we respond with this


#ifndef USB_COMMS_H
#define USB_COMMS_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

#define SYNC_BYTE       0xFF
#define READY_BYTE      0xAA

extern volatile FlowState flow_state;
extern volatile uint8_t rx_buffer[sizeof(RxPacket)];
extern uint8_t ready_message[] = {SYNC_BYTE, 0x01, READY_BYTE};

typedef struct __attribute__((packed)) {
    uint8_t sync_byte;
    uint16_t control_byte;
    float forces[6];
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