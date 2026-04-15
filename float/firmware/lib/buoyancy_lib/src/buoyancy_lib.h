#ifndef BUOYANCY_LIB_H
#define BUOYANCY_LIB_H
#include <tmc_interfacer.h>
#include <control_lib.h>
#define MS 256
#define RMS_CURRENT 800
// #define K_P 0.086
#define K_P 1.2
// #define K_I 0.00879 / 7
#define K_I 0.00879 / 3
// #define K_D 0.187
#define K_D 100
#define MAX_MOTOR_VEL 0.032
// #define MAX_MOTOR_VEL 100000
#define MAX_DISTANCE 10
#define MAX_ROTATIONS 12

void buoyancy_setup();
void buoyancy_loop(float depth);


#endif