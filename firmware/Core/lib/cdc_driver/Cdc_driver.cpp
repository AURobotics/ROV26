#include "Cdc_driver.h"
#include "usbd_cdc_if.h"

Cdc_driver* g_cdc_driver = nullptr;
extern "C" void on_cdc_isr(uint8_t* buf, uint32_t len) {
    if (g_cdc_driver != nullptr)
        g_cdc_driver->on_data_receive(buf, len);
 }

void Cdc_driver::setup() {
    if (g_cdc_driver == nullptr)
        g_cdc_driver = this;
}

bool Cdc_driver::available() {
    // if both are equal (0,0) -> empty buffer
    return m_read_index != m_write_index;
}

bool Cdc_driver::parse(uint8_t* buf, uint32_t len, GenericMessage& out) {
    if (len < 2 || buf[0] != 0xFF)
        return false;

    auto type = static_cast<Message_Type>(buf[1]);

    switch (type) {
    case READY_MESSAGE :
        if (len < sizeof(Ready_msg))
            return false;

        out.data.ready_msg = *reinterpret_cast<const Ready_msg*>(buf);
        out.type = READY_MESSAGE;
        out.size = sizeof(Ready_msg);
        break;

    case COMMAND_MESSAGE :
        if (len < sizeof(Command_msg))
            return false;

        out.data.command_msg = *reinterpret_cast<const Command_msg*>(buf);
        out.type = COMMAND_MESSAGE;
        out.size = sizeof(Command_msg);
        break;

    case OPERATION_MESSAGE :
        if (len < sizeof(Operation_Mode_Msg))
            return false;

        out.data.operation_msg = *reinterpret_cast<const Operation_Mode_Msg*>(buf);
        out.type = OPERATION_MESSAGE;
        out.size = sizeof(Operation_Mode_Msg);
        break;

    case PARAMETERS_MESSAGE :
        if (len < sizeof(Parameter_Msg))
            return false;

        out.data.param_msg = *reinterpret_cast<const Parameter_Msg*>(buf);
        out.type = PARAMETERS_MESSAGE;
        out.size = sizeof(Parameter_Msg);
        break;

    case TUNING_MESSAGE :
        if (len < sizeof(Tuning_Msg))
            return false;

        out.data.tuning_msg = *reinterpret_cast<const Tuning_Msg*>(buf);
        out.type = TUNING_MESSAGE;
        out.size = sizeof(Tuning_Msg);
        break;

    default :
        return false;
    }

    return true;
}

void Cdc_driver::on_data_receive(uint8_t* buf, uint32_t len) {
    // writes in the next slot and advances the write index
    RawData& slot = m_slots[m_write_index];
    memcpy(slot.data, buf, len);
    slot.len = len;
    m_write_index = (m_write_index + 1) % BUFFER_SIZE;
}

Message_Type Cdc_driver::read_msg(GenericMessage& msg) {
    RawData& slot = m_slots[m_read_index];
    parse(slot.data, slot.len, msg);      
    m_read_index = (m_read_index + 1) % BUFFER_SIZE;
    return msg.type;
}

bool Cdc_driver::write_msg(GenericMessage* msg) {
    auto result = CDC_Transmit_FS(reinterpret_cast<uint8_t*>(msg), sizeof(GenericMessage));
    return result == USBD_OK;
}
