#include <control_lib.h>


PID::PID(float Kp, float Ki, float Kd, float Kg, float max_position){
    this->Kp = Kp;
    this->Ki = Ki;
    this->Kd = Kd;
    this->Kg = Kg;
    this->max_position = max_position;
}

float PID::calculate_error(float current_reading){
    return this->current_set_point - current_reading;
}

void PID::set_reference_time(float time){
    this->prev_time = time;
}

float PID::calculate_PID(float error, float time_stamp){
    float P = this->Kp * error;
    this->current_integral += error * (time_stamp - this->prev_time);
    float I = this->Ki * this->current_integral;
    //anti windup starts here
    if(I > this->max_position){ 
        this->current_integral = this->max_position / Ki;
        I = this->current_integral * this->Ki;
    }
    else if(I < -this->max_position){
        this->current_integral = -this->max_position / Ki;
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
    float PID = (P+I+D) * this->Kg;
    if(PID > this->max_position){
        PID = this->max_position;
    }
    else if(PID < -this->max_position){
        PID = -this->max_position;
    }
    // TODO REMOVE PRINTS:
    Serial.print("PID:");
    Serial.print(P);
    Serial.print(",");
    Serial.print(I);
    Serial.print(",");
    Serial.println(D);
    return PID;
}


double PID::control_loop(float height) {
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
  if(!hold_position && error < 0.1){ //error less than 30 cm
    hold_position = true; //start holding position
    Time = millis();
  }
  float signal = this->calculate_PID(error, millis());
  return signal;
}

double getDepth(){
    int reading = analogRead(39);
    double depth = 0.001210352 * reading;
    return depth;
}