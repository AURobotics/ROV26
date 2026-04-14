#ifndef BUOYANCY_LIB_H
#define BUOYANCY_LIB_H
#include <tmc_interfacer.h>
#include <control_lib.h>
#define MS 256
#define RMS_CURRENT 800
#define K_P 0.086
#define K_I 0.00879 / 7
#define K_D 0.187
#define MAX_MOTOR_VEL 4 * POWER_SCREW_SIZE //basically, 4 rotations per second
// #define MAX_MOTOR_VEL 100000
#define MAX_DISTANCE 10
#define MAX_ROTATIONS 12

TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS, MAX_MOTOR_VEL);
PID pid = PID(K_P, K_I, K_D, MAX_MOTOR_VEL);

void buoyancy_setup();
void buoyancy_loop(float depth);


#endif