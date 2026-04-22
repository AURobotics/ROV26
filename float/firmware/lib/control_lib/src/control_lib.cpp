#include <control_lib.h>


PID::PID(float Kp, float Ki, float Kd, float max_position, float* set_points, int set_points_num){
    this->Kp = Kp;
    this->Ki = Ki;
    this->Kd = Kd;
    this->max_position = max_position * 0.95;
    this->min_position = - max_position;
    this->set_points = set_points;
    this->set_points_num = set_points_num;
}

float PID::calculate_error(float current_reading){
    return this->set_points[this->current_setpoint_idx] - current_reading;
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
    float error = this->calculate_error(height);

    if(hold_position){ //if we have been holding position for 30 seconds, we flip direction
        if(abs(error) > 0.3){
            Time = millis(); //if error increases above 30cm again, restart the holding timer
            hold_position = false;
        }
        if((millis() - Time > holding_time)){
            if(this->current_setpoint_idx < this->set_points_num - 1)
                this->current_setpoint_idx++;
            else
                this->sequence_done = true;
            hold_position = false;
        }
    }
    if(!hold_position && abs(error) < 0.3){ //error less than 30 cm
        hold_position = true; //start holding position
        Time = millis();
    }
    int signal = this->calculate_PID(error, millis());

    return signal;
}

// float getDepth(){
//     int reading = analogRead(39);
//     float depth = 0.001210352 * reading;
//     return depth;
// }

float current_depth = 0;

float getDepth(){
    char mod = 'f';
    if(Serial.available() > 0)
        mod = Serial.read();
    if(mod == 'i')
        current_depth += 0.2;
    else if(mod == 'd')
        current_depth -= 0.2;
    else if(mod == 'h')
        current_depth = -100;
    return current_depth;
}