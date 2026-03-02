#include "usb_comms.h"
#include "main.h"
#include <cstring>



// volatile FlowState flow_state = FLOW_RECEIVING;


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

