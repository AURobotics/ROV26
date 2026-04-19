#include <control_lib.h>


PID::PID(float Kp, float Ki, float Kd, float max_position){
    this->Kp = Kp;
    this->Ki = Ki;
    this->Kd = Kd;
    this->max_position = max_position * 0.95;
    this->min_position = - max_position;
}

float PID::calculate_error(float current_reading){
    return this->current_set_point - current_reading;
}

void PID::set_reference_time(unsigned long Time){
    this->prev_time = Time;
}

int PID::calculate_PID(float error, unsigned long time_stamp){
    if(time_stamp - this->prev_time < sampling_time)
        return this->PID_output;

    float P = this->Kp * error;
    float integral_increment = error * (time_stamp - this->prev_time);
    this->current_integral += integral_increment;
    float I = this->Ki * this->current_integral;
    float D;
    D = Kd * (error - this->prev_error) / (time_stamp - this->prev_time);
    this->prev_error = error;
    this->prev_time = time_stamp;
    this->prev_D = D;
    float PID = (P+I+D);
    //anti windup
    if(PID >= this->max_position){
        // PID = this->max_position;
        this->current_integral -= integral_increment;
        PID = this->max_position;
    }
    else if(PID <= this->min_position){
        this->current_integral -= integral_increment;
        PID = this->min_position;
    }
    this->PID_output = PID;

    // TODO REMOVE PRINTS:
    Serial.print("PID:");
    Serial.print(P);
    Serial.print(",");
    Serial.print(I);
    Serial.print(",");
    Serial.println(D);
    return PID;
}


int PID::control_loop(float height) {
  if(hold_position && (millis() - Time > holding_time)){ //if we have been holding position for 30 seconds, we flip direction
    if(current_set_point == set_point1){ //flip motor direction after being stable for 30 seconds
        current_set_point = set_point2;
    }
    else{
        current_set_point = set_point1;
    }
    // this->current_integral = 0; //reset integral to help change direction faster
    hold_position = false;
  }
  float error = this->calculate_error(height);
  if(!hold_position && error < 0.1){ //error less than 10 cm
    hold_position = true; //start holding position
    Time = millis();
  }
  int signal = this->calculate_PID(error, millis());
  return signal;
}

double getDepth(){
    int reading = analogRead(4);
    double depth = 0.001210352 * reading;
    return depth;
}