#ifndef BUOYANCY_LIB_H
#define BUOYANCY_LIB_H
#include <tmc_interfacer.h>
#include <control_lib.h>
#define MS 256
#define RMS_CURRENT 800
#define K_P 600
#define K_I 0
#define K_D 650
#define MAX_MOTOR_SPS 100 //make motor steps per second
// #define MAX_MOTOR_VEL MAX_MOTOR_SPS / 200 * POWER_SCREW_SIZE
#define MAX_MOTOR_VEL 101
#define MAX_ROTATIONS 12.5
// #define MAX_DISTANCE 8 * MAX_ROTATIONS //96mm
#define MAX_DISTANCE 1300 //1300 steps up and down
#define FLOAT_HEIGHT 0.5

const int EEPROM_SIZE = sizeof(float);


bool buoyancy_setup(bool read_EEPROM);
void buoyancy_loop(float depth);
void save_rotations();
float getCurrentTarget();
bool isComplete();

#endif