#include <Arduino.h>

class PID{
    public:
        PID(float Kp, float Ki, float Kd, float max_motor_output){
            this->Kp = Kp;
            this->Ki = Ki;
            this->Kd = Kd;
            float max_clearance = 0.98; //better practice to assume the motor cant reach 100% output, this variable is used for windup checking
            this->max_motor_output = max_motor_output * max_clearance;
        }
        float Kp, Ki, Kd;
        float max_motor_output;
        float current_integral = 0;
        float prev_error = 0;
        float prev_time = 0;
        float calculate_PID(float error, float time_stamp){
            float P = this->Kp * error;
            this->current_integral += error * (time_stamp - this->prev_time);
            float I = this->Ki * this->current_integral;
            //anti windup starts here
            if(I > this->max_motor_output){ 
                this->current_integral = this->max_motor_output / Ki;
                I = this->current_integral * this->Ki;
            }
            else if(I < -this->max_motor_output){
                this->current_integral = -this->max_motor_output / Ki;
                I = this->current_integral * this->Ki;
            }
            //anti windup ends here
            float D = Kd * (error - this->prev_error) / (time_stamp - this->prev_time);
            this->prev_error = error;
            this->prev_time = time_stamp;
            float PID = P+I+D;
            if(PID > this->max_motor_output){
                PID = this->max_motor_output;
            }
            else if(PID < -this->max_motor_output){
                PID = -this->max_motor_output;
            }
            return PID;
        }
};

void setup() {
// write your initialization code here
}

void loop() {
// write your code here
}