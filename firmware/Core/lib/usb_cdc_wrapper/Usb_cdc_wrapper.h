#ifndef FIRMWARE_USB_CDC_WRAPPER_H
#define FIRMWARE_USB_CDC_WRAPPER_H
#include <cstdint>
#include <sys/types.h>
#include "usb_comms.h"
#include "usbd_cdc_if.c"


#ifdef __cplusplus
extern "C" {
#endif
void on_cdc_isr(uint8_t* buf, uint32_t len);
#ifdef __cplusplus
}
#endif

#ifdef __cplusplus

extern Usb_cdc_wrapper usb_cdc;

typedef struct {
    Message_Type type;
    uint16_t size;

    union  {
        Ready_msg ready_msg;
        Command_msg command_pkt;
        Operation_Mode_Msg operation_msg;
        Parameter_Msg param_msg;
        Tuning_Msg tuning_msg;
        uint8_t raw[32];  // to garuantee having space for all messages 
    }data;

} GenericMessage;

class Usb_cdc_wrapper {
    uint32_t m_timeout_ms{};
    bool data_received = false;
    uint8_t m_rx_buffer[256]{};
    uint16_t rx_len{};
    static constexpr uint8_t BUFFER_SIZE = 2;

    GenericMessage m_slots[BUFFER_SIZE]{}; //actual address that messages are written to and read from

    volatile uint8_t m_write_index{0}; 
    volatile uint8_t m_read_index{0}; 

public:
    explicit constexpr Usb_cdc_wrapper(uint32_t m_timeout) : m_timeout_ms(m_timeout) {}
    bool available();
    bool write_msg(TxPacket* tx);
    GenericMessage read_msg(); 
    void onDataReceived(uint8_t* buf, uint32_t len);
    bool parse(uint8_t* buf, uint32_t len, GenericMessage& out);
};

#endif
#endif // FIRMWARE_USB_CDC_WRAPPER_H
