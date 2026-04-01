#ifndef CALIBRATION_H
#define CALIBRATION_H   

#include <Arduino.h>
#include <TMCStepper.h>
#include <HardwareSerial.h>

#define R_SENSE 0.11f
#define RX_PIN 16 
#define TX_PIN 17


void calibration_setup(int rms_current, int ms);
void calibration_loop(int ms);
void readSerialAndRespond(int ms);



#endif