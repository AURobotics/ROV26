#include <global_functions.h>

//TODO fix stop motor on going backwards

TMC_interfacer::TMC_interfacer(int ms, float max_rotations){
    this->ms = ms;
    this->max_rotations = max_rotations;
}

float TMC_interfacer::VACTUAL2SPS(uint32_t VACTUAL){
    return (int) VACTUAL / this->ms * this->oscillator_multiplier;
    // return VACTUAL * this->oscillator_multiplier;
}

uint32_t TMC_interfacer::SPS2VACTUAL(int steps){
    return steps * this->ms / this->oscillator_multiplier;
    // return steps / this->oscillator_multiplier;
}
void TMC_interfacer::stop_motor(bool shutdown){
    Serial.println("stopping motor...");
    float velocity = VACTUAL2SPS(driver.VACTUAL());
    while(velocity >= 10){
        velocity -= 10;
        driver.VACTUAL(SPS2VACTUAL(velocity));
        delay(100);
    }
    while(velocity <= -10){
        velocity += 10;
        driver.VACTUAL(SPS2VACTUAL(velocity));
        delay(100);

    }
    if(shutdown){
        driver.toff(0);
        Serial.println("motor stopped successfully!");
        Serial.println("input any key to continue...");
        while(!(Serial.available() > 0)){
            delay(100);
        }
        Serial.read();
        driver.toff(5);
        this->manual_ramp();
    }
}

void TMC_interfacer::readSerialAndRespond() {
  if (Serial.available() > 0) {  // Check if data is available
    char receivedChar = Serial.read();  // Read a single character
    
    if (receivedChar == 'h') {  // Check if it matches 'h'
      stop_motor(true);
    }
  }
}

void TMC_interfacer::normal_setup(int rms_current, int steps_per_second){
    driver.begin(); 
    delay(500);
    driver.pdn_disable(true); 
    driver.toff(5); 
    driver.pwm_autoscale(true); 
    driver.I_scale_analog(false);
    driver.rms_current(rms_current); 
    driver.mstep_reg_select(true);
    driver.microsteps(this->ms);
    if(this->ms == 0)
        this->ms += 1;
    Serial.println("starting in 5 seconds: ");
    driver.toff(0); 
    delay(1000);
    Serial.println("started!");
    driver.toff(5); 
    driver.VACTUAL(SPS2VACTUAL(steps_per_second));
}

void TMC_interfacer::manual_ramp(){
    int velocity = 10;
    Serial.println("MANUAL RAMP MODE");
    while(true){
        while(Serial.available() <= 0)
            delay(10);
        char receivedChar = Serial.read();
        if(receivedChar == 'u'){
            velocity += 10;
            Serial.print("velocity before sending: ");
            Serial.println(velocity);
            driver.VACTUAL(SPS2VACTUAL(velocity));
            uint32_t vel = driver.VACTUAL();
            Serial.print("current vactual: ");
            Serial.println(vel);
            Serial.print("steps per second: ");
            Serial.println(VACTUAL2SPS(vel));
        }
        else if(receivedChar == 'd'){
            velocity -= 10;
            driver.VACTUAL(SPS2VACTUAL(velocity));
            uint32_t vel = driver.VACTUAL();
            Serial.print("current vactual: ");
            Serial.println(vel);
            Serial.print("steps per second: ");
            Serial.println(VACTUAL2SPS(vel));
        }
        else if(receivedChar == 'h'){
            stop_motor(true);
        }
        else if(receivedChar == 'c'){
            break;
        }
    }
}
void TMC_interfacer::calibrate(){
    driver.VACTUAL(SPS2VACTUAL(6));
    delay(130);
    driver.pwm_autograd(true);
    uint8_t pwm_ofs = driver.pwm_ofs_auto();
    Serial.print("pwm_ofs_auto: ");
    Serial.println(pwm_ofs);
}

void TMC_interfacer::calibration_loop(){
    uint16_t pwm_scale_auto_val = driver.pwm_scale_auto();
    Serial.print("pwm_scale_auto: ");
    Serial.println(pwm_scale_auto_val);
    uint8_t pwm_grad = driver.pwm_grad_auto();
    Serial.print("pwm_grad_auto: ");
    Serial.println(pwm_grad);
    
}

void TMC_interfacer::measure_position(){
    current_sequencer = driver.MSCNT();
    int sequence_difference = current_sequencer - prev_sequencer;

    if(!going_forward)
        sequence_difference = -sequence_difference; //flip direction
    
    if(sequence_difference < 0){
        sequence_difference += 1024; //1023 -> maximum value MSCNT can hold
    }
    int step_difference = sequence_difference / 256; //every 256, a step has been made
    int remainder = sequence_difference % 256;
    if(step_difference >= 1){
        if(going_forward){
            rotations += (step_difference/(float)STEPS); 
        }
        else{
            rotations -= (step_difference/(float)STEPS); 
        }
        prev_sequencer = current_sequencer - remainder;
    }
    // Serial.print("s:");
    // Serial.println(current_sequencer);
    // Serial.print("prev sequencer: ");
    // Serial.println(prev_sequencer);
    // Serial.print("step_difference: ");
    // Serial.println(step_difference);
    // Serial.print("remainder: ");
    // Serial.println(remainder);
    // Serial.print("r:");
    // Serial.println(rotations);
    // Serial.print("time: ");
    // Serial.println(time);




    // if(rotations - prev_rotations >= 1){
    //     Serial.print("r: ");
    //     Serial.println(rotations);
    //     prev_rotations = rotations;
    // }
    if (rotations >= 10){
      Serial.println("DONE 10 ROTATIONS!");
    //   stop_motor(true);
    //   delay(10000);
    }
}

bool TMC_interfacer::set_velocity(double velocity){
    if(rotations - max_rotations < 1){ //1 rotation is a threshhold
        stop_motor(false);
        return false;
    }
    float SPS = velocity / (POWER_SCREW_SIZE  * 0.001) / STEPS;
    driver.VACTUAL(SPS2VACTUAL(SPS));
    return true;
}
