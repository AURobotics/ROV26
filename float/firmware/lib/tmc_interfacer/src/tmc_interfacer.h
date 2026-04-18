#ifndef TMC_INTERFACER_H
#define TMC_INTERFACER_H    
#include <Arduino.h>
#include <TMCStepper.h>
#include <HardwareSerial.h>

#define R_SENSE 0.11f
// #define RX_PIN 16 
// #define TX_PIN 17
#define RX_PIN 18
#define TX_PIN 17
#define STEPS 200
#define POWER_SCREW_SIZE 8 //mm
#define DIR_PIN 23
#define STEP_PIN 22

class TMC_interfacer{
    public:
        TMC_interfacer(int ms, float max_rotations, float max_motor_velocity);
        uint16_t micro_steps = 0;
        float rotations = 0;
        float prev_rotations = 0;
        int current_sequencer = 0;
        int prev_sequencer = 0;
        int ms;
        int fast_decceleration_threshold = 25;
        int fast_deceleration_step = 25;
        float max_rotations;
        float max_distance;
        float max_motor_velocity;
        float oscillator_multiplier = 0.715;
        bool going_forward = true; //false if rotating the other direction
        bool motor_stopped = false;
        TMC2208Stepper driver = TMC2208Stepper(&Serial2, R_SENSE);
        void normal_setup(int rms_current, int steps_per_second);
        void STEPDIR_setup(int rms_current);
        void readSerialAndRespond();
        void measure_position();
        void stop_motor();
        int VACTUAL2SPS(uint32_t VACTUAL);
        uint32_t SPS2VACTUAL(int steps);
        bool set_velocity(int velocity);
        int V2SPS(float velocity);
        void manual_ramp();
        void disable_motor();
        void adjust_velocity(float target_position);
        void adjust_velocity_STEPDIR(float target_position);
        float POS2ROTS(float pos); //position to rotations
        float ROTS2POS(float rotations);
        float SPS2V(int SPS);
};

#endif