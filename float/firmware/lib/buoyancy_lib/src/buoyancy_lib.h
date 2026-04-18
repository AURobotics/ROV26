#ifndef BUOYANCY_LIB_H
#define BUOYANCY_LIB_H
#include <tmc_interfacer.h>
#include <control_lib.h>
#define MS 256
#define RMS_CURRENT 800
#define K_P 0.086 / 100
#define K_I 0.00879 / 1000
#define K_D 0.187 * 5
#define K_G 0.25 //total gain
#define MAX_MOTOR_SPS 400 //make motor steps per second
#define MAX_MOTOR_VEL MAX_MOTOR_SPS / 200 * POWER_SCREW_SIZE
#define MAX_ROTATIONS 13
#define MAX_DISTANCE 8 * MAX_ROTATIONS //96mm
#define FLOAT_HEIGHT 500

const int EEPROM_SIZE = sizeof(float) + 1;


void buoyancy_setup();
void buoyancy_loop(float depth);


#endif