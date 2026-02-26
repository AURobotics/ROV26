#include <comms.h>

volatile FlowState flow_state = FLOW_RECEIVING;
volatile uint8_t data_received = 0;
volatile uint8_t rx_buffer[sizeof(RxPacket)];
uint8_t ready_byte = READY_BYTE;


void load_tx(TxPacket *tx){
	tx->sync_byte = SYNC_BYTE;
	tx->depth = 1;
	tx->yaw = 1;
	tx->pitch = 1;
	tx->roll = 1;
}