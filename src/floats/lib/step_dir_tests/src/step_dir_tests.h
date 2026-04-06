#ifndef STEP_DIR_TESTS_H
#define STEP_DIR_TESTS_H   


#include <Arduino.h>
#define EN_PIN 21
#define STEP_PIN 22
#define DIR_PIN 23
#define STEPS_PER_REVOLUTION 200

void calibrate();
void accelerate();
void test_setup();
void test_loop();
#endif