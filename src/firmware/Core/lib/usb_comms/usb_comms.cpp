#include "usb_comms.h"
#include <cstring>
#include "main.h"


// volatile FlowState flow_state = FLOW_RECEIVING;
// uint8_t data_received = 0;
// uint8_t rx_buffer[PAYLOAD_SIZE];
// uint8_t ready_byte = READY_BYTE;
// uint32_t last_receive_time;
// RxPacket rx_pkt;


// void load_tx(TxPacket *tx){
// 	tx->sync_byte = SYNC_BYTE;
// 	// read sensor data
// 	// assuming bno and ms5611 are global variables defined in main or something like that
// 	tx->depth = ms5611::getDepth();
// 	vec_3 euler = bno055::get_euler_angles();
// 	tx->yaw = euler.z();
// 	tx->pitch = euler.y();
// 	tx->roll = euler.x();
// }
