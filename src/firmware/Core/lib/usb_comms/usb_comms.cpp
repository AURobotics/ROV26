#include "usb_comms.h"
#include "main.h"
#include "bno055.h"
#include "ms5611.h"

extern MS5611 ms5611;
extern BNO055 bno055;

volatile FlowState flow_state = FLOW_RECEIVING;
volatile uint8_t data_received = 0;
volatile uint8_t rx_buffer[PAYLOAD_SIZE];
uint8_t ready_byte = READY_BYTE;


void load_tx(TxPacket *tx){
	tx->sync_byte = SYNC_BYTE;
	// read sensor data
	// assuming bno and ms5611 are global variables defined in main or something like that
	tx->depth = ms5611::getDepth()
	vec_3 euler = bno055::get_euler_angles();
	tx->yaw = euler.z();
	tx->pitch = euler.y();
	tx->roll = euler.x();
}
