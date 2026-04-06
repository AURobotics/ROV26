#ifndef GLOBAL_FUNCTIONS_H
#define GLOBAL_FUNCTIONS_H    
#include <Arduino.h>
#include <TMCStepper.h>
#include <HardwareSerial.h>

#define R_SENSE 0.11f
#define RX_PIN 16 
#define TX_PIN 17
#define STEPS 200
#define STEP_PIN 22
#define DIR_PIN 23

class TMC_interfacer{
    public:
        TMC_interfacer(int ms);
        uint16_t micro_steps = 0;
        float rotations = 0;
        float prev_rotations = 0;
        int current_sequencer = 0;
        int prev_sequencer = 0;
        int ms;
        float oscillator_multiplier = 0.715;
        bool going_forward = true; //false if rotating the other direction
        TMC2208Stepper driver = TMC2208Stepper(&Serial2, R_SENSE);
        void normal_setup(int rms_current, int steps_per_second);
        void readSerialAndRespond();
        void measure_position();
        void stop_motor(bool shutdown);
        void manual_ramp();
        float VACTUAL2SPS(uint32_t VACTUAL);
        uint32_t SPS2VACTUAL(int steps);
        void step_dir_ramp();
        void single_step();
        void calibrate();
        void calibration_loop();

};

#endif