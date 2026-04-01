#include <control_lib.h>


PID::PID(float Kp, float Ki, float Kd, float max_motor_output){
    this->Kp = Kp;
    this->Ki = Ki;
    this->Kd = Kd;
    float max_clearance = 0.98; //better practice to assume the motor cant reach 100% output, this variable is used for windup checking
    this->max_motor_output = max_motor_output * max_clearance;
}

float PID::calculate_error(float current_reading){
    return this->set_point - current_reading;
}
float PID::calculate_PID(float error, float time_stamp){
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
    float D;
    if(time_stamp - this->prev_time == 0) //make sure to not divide by 0
        D = prev_D;
    else
        D = Kd * (error - this->prev_error) / (time_stamp - this->prev_time);
    this->prev_error = error;
    this->prev_time = time_stamp;
    this->prev_D = D;
    float PID = P+I+D;
    if(PID > this->max_motor_output){
        PID = this->max_motor_output;
    }
    else if(PID < -this->max_motor_output){
        PID = -this->max_motor_output;
    }
    return PID;
}

float time;
bool hold_position = false;


double control_loop(PID pid) {
  // put your main code here, to run repeatedly:
  if(hold_position && millis() - time > 1000 * 30){ //if we have been holding position for 30 seconds, we flip direction
    pid.set_point = -2.5 - pid.set_point; //flip motor direction after being stable for 30 seconds
    pid.current_integral = 0; //reset integral to help change direction faster
    hold_position = false;
  }
  float height = get_height(); //get height from pressure sensor
  float error = pid.calculate_error(height);
  if(!hold_position && error < 0.3){ //error less than 30 cm
    hold_position = true; //start holding position
    time = millis();
  }
  float signal = pid.calculate_PID(error, millis());
//   driver.VACTUAL(signal);
  return signal;
}