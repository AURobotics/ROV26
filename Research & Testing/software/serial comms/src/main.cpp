#include <Arduino.h>
#include <comms.h>

uint8_t ready_message[] = {SYNC_BYTE, 0x01, READY_BYTE};

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
    case FLOW_WAITING:
        // Clear buffer of any leftover garbage before signaling ready
        while (Serial.available() > 0)
            Serial.read();

        Serial.write(ready_message, sizeof(ready_message));
        flow_state = FLOW_RECEIVING;
        break;

    case FLOW_RECEIVING:
    {
        // 1. Wait for the SYNC_BYTE to appear
        if (Serial.available() > 0)
        {
            if (Serial.peek() == SYNC_BYTE)
            {

                uint32_t start_wait = millis();
                size_t bytes_read = 0;
                uint8_t *raw_ptr = (uint8_t *)&rx_pkt;

                // 2. Try to read the full sizeof(RxPacket) within 10ms
                while (bytes_read < sizeof(RxPacket))
                {
                    // Check for 10ms timeout
                    if (millis() - start_wait >= 40)
                    {
                        Serial.println("reset");
                        // TIMEOUT: Don't block, just go back to waiting/ready
                        flow_state = FLOW_WAITING;
                        return;
                    }

                    if (Serial.available() > 0)
                    {
                        raw_ptr[bytes_read++] = Serial.read();
                    }
                }

                // 3. Success: We have a full packet
                // Since rx_pkt is now populated, move to sending
                flow_state = FLOW_SENDING;
            }
            else
            {
                // Garbage byte at the start? Clear it and stay in RECEIVING
                Serial.read();
            }
        }
        break;
    }

    case FLOW_SENDING:
        Serial.println("sending");
        if (millis() - last_send_time >= 40)
        {
            last_send_time = millis();
            load_tx(&tx_pkt);
            // Ensure the TxPacket also has its sync byte set
            tx_pkt.sync_byte = SYNC_BYTE;
            Serial.write((const uint8_t *)&tx_pkt, sizeof(TxPacket));

            // Go back to waiting for the next command
            flow_state = FLOW_WAITING;
        }
        break;
    }
}