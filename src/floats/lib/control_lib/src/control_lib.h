#ifndef CONTROL_LIB_H
#define CONTROL_LIB_H
#include <Arduino.h>


class PID{
    public:
        PID(float Kp, float Ki, float Kd, float max_motor_output);
        float Kp, Ki, Kd;
        float max_motor_output;
        float current_integral = 0;
        float prev_error = 0;
        float prev_time = 0;
        float prev_D = 0;
        float set_point;
        int holding_time = 30 * 1000; //hold position for 30 seconds
        float Time = millis();
        bool hold_position = false;
        float calculate_error(float current_reading);
        float calculate_PID(float error, float time_stamp);
        double control_loop();


};
float get_height();
#endif