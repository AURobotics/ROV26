#ifndef FIRMWARE_USB_CDC_WRAPPER_H
#define FIRMWARE_USB_CDC_WRAPPER_H
#include <cstdint>
#include <sys/types.h>


#ifdef __cplusplus
extern "C" {
#endif
void on_cdc_isr(uint8_t* buf, uint32_t len);
#ifdef __cplusplus
}
#endif

#ifdef __cplusplus

class Usb_cdc_wrapper {
    uint32_t m_timeout_ms{};
    bool data_received = false;
    uint8_t m_rx_buffer[256]{};
    uint16_t rx_len{};
public:
    explicit constexpr Usb_cdc_wrapper(uint32_t m_timeout) : m_timeout_ms(m_timeout) {}
    bool available();
    bool write_msg();
    bool read_msg();
    bool available() const;
    void onDataReceived(uint8_t* buf,uint32_t len);
};

#endif
#endif // FIRMWARE_USB_CDC_WRAPPER_H
