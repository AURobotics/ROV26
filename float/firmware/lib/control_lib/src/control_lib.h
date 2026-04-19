#ifndef CONTROL_LIB_H
#define CONTROL_LIB_H
#include <Arduino.h>


class PID{
    public:
        PID(float Kp, float Ki, float Kd, float max_position);
        float Kp, Ki, Kd;
        float max_position;
        float min_position;
        float max_position_clearance_percentage = 0.95;
        float current_integral = 0;
        float prev_error = 0;
        unsigned long prev_time = 0;
        float prev_D = 0;
        float current_set_point;
        float set_point1;
        float set_point2;
        int holding_time = 30 * 1000; //hold position for 30 seconds
        unsigned long sampling_time = 50;
        float PID_output;
        unsigned long Time = millis();
        bool hold_position = false;
        float calculate_error(float current_reading);
        int calculate_PID(float error, unsigned long time_stamp);
        int control_loop(float height);
        void set_reference_time(unsigned long Time);


};
double getDepth();
#endif