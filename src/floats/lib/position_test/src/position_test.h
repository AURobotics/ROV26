#ifndef POSITION_TEST_H
#define POSITION_TEST_H    
#include <Arduino.h>
#include <TMCStepper.h>
#include <HardwareSerial.h>

#define R_SENSE 0.11f
#define RX_PIN 16 
#define TX_PIN 17

void normal_setup(int rms_current, int ms);

#endif