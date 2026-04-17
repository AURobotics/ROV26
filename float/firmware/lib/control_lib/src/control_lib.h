#ifndef CONTROL_LIB_H
#define CONTROL_LIB_H
#include <Arduino.h>


class PID{
    public:
        PID(float Kp, float Ki, float Kd,float Kg, float max_position);
        float Kp, Ki, Kd, Kg;
        float max_position;
        float current_integral = 0;
        float prev_error = 0;
        float prev_time = 0;
        float prev_D = 0;
        float current_set_point;
        float set_point1;
        float set_point2;
        int holding_time = 30 * 1000; //hold position for 30 seconds
        float Time = millis();
        bool hold_position = false;
        float calculate_error(float current_reading);
        float calculate_PID(float error, float time_stamp);
        double control_loop(float height);
        void set_reference_time(float time);


};
double getDepth();
#endif