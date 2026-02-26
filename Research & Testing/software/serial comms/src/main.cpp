#include <Arduino.h>
#include <comms.h>

volatile uint32_t last_send_time = 0;

void setup()
{
    Serial.begin(9600);
}

void loop()
{

    RxPacket rx_pkt;
    TxPacket tx_pkt;
    switch (flow_state)
    {
    case FLOW_RECEIVING:
        if (data_received)
        {
            data_received = 0;
            memcpy(&rx_pkt, const_cast<const uint8_t *>(rx_buffer), sizeof(RxPacket));
            flow_state = FLOW_SENDING;
        }
        else
        {
            flow_state = FLOW_WAITING; // no data received, signal Pi
        }
        break;

    case FLOW_WAITING:
        Serial.write(ready_byte);
        flow_state = FLOW_RECEIVING;
        break;

    case FLOW_SENDING:
        if (millis() - last_send_time >= 40)
        {
            last_send_time = millis();
            load_tx(&tx_pkt);
            Serial.write((const uint8_t *)&tx_pkt, sizeof(TxPacket));
            flow_state = FLOW_RECEIVING;
        }
        break;
    }
}