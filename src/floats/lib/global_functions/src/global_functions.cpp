#include <global_functions.h>

//TODO fix stop motor on going backwards

TMC_interfacer::TMC_interfacer(int ms){
    this->ms = ms;
    // this->ms = 1;
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
    delay(5000);
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
            velocity += 5;
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
            velocity -= 5;
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
    int max_iterations = 50 * this->ms;
    for(int i = 0; i < max_iterations; i++){
        digitalWrite(STEP_PIN, HIGH);
        // delay((float)83/(this->ms)); 
        delayMicroseconds(((float) 41.5/(this->ms))*1000);
        digitalWrite(STEP_PIN, LOW);
        // delay((float)83/(this->ms));
        delayMicroseconds(((float) 41.5/(this->ms))*1000);
    }
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
void TMC_interfacer::single_step(){
    char receivedChar;
    while(true){
        while(Serial.available() <= 0)
            delay(10);
        receivedChar = Serial.read();
        if(receivedChar == 's'){
            Serial.println("STEP");
            digitalWrite(STEP_PIN, HIGH);
            delayMicroseconds(160); 
            digitalWrite(STEP_PIN, LOW);
        }
        else if(receivedChar == 'd'){
            driver.shaft(!driver.shaft());
            delay(5);
        }
        else if(receivedChar == 'z'){
            for(int i = 0; i < 100; i++){
                digitalWrite(STEP_PIN, HIGH);
                delay(10);
                digitalWrite(STEP_PIN, LOW);
                delay(10);
            }
        }
        else if(receivedChar == 'h'){
            stop_motor(true);
        }
    }
}

void TMC_interfacer::step_dir_ramp(){
    char receivedChar;
    int time_delay = 0.1 * 1000;
    while(true){
        digitalWrite(STEP_PIN, HIGH);
        delayMicroseconds(time_delay);
        digitalWrite(STEP_PIN, LOW);
        delayMicroseconds(time_delay);
        if(Serial.available() > 0){
            receivedChar = Serial.read();
            if(receivedChar == 'u'){
                time_delay = 0.01 * 1000;
            }
            else if(receivedChar == 'd'){
                time_delay = 0.1 * 1000;
            }
            else if(receivedChar == 'h'){
                driver.toff(0);
                delay(100000);
            }
            // else if(receivedChar == 'c'){
            //     break;
            // }
            Serial.print("time delay: ");
            Serial.println(time_delay);
        }
    }
}
void TMC_interfacer::measure_position(){
    //TODO HANDLE BACKWORD ROTATION COUNTING
    //TODO HANDLE POSITION ACCURACY (about 30 degree error per rotation)
    current_sequencer = driver.MSCNT();
    int sequence_difference = current_sequencer - prev_sequencer;
    if(sequence_difference < 0){
        sequence_difference += 1023; //1023 -> maximum value MSCNT can hold
    }
    int step_difference = sequence_difference / 256; //every 256, a step has been made
    int remainder = sequence_difference % 256;
    if(step_difference >= 1){
        rotations += (sequence_difference/(float)STEPS); 
        prev_sequencer = current_sequencer - remainder;
    }
    int time = millis();
    // Serial.printf("current_sequencer: %d %d\n", current_sequencer, time);
    // Serial.printf("sequence_difference: %d %d\n", sequence_difference, time);
    // Serial.printf("step_difference: %d %d\n", step_difference, time);
    // Serial.printf("step_remainder: %d %d\n", remainder, time);
    // Serial.printf("rotations_increment: %d %d\n", sequence_difference/(float)STEPS, time);
    // Serial.printf("rotations: %d %d\n", rotations, time);
    Serial.print("current sequencer: ");
    Serial.println(current_sequencer);
    Serial.print("prev sequencer: ");
    Serial.println(prev_sequencer);
    Serial.print("step_difference: ");
    Serial.println(step_difference);
    Serial.print("rotations: ");
    Serial.println(rotations);
    Serial.print("time: ");
    Serial.println(time);




    // if(rotations - prev_rotations >= 1){
        // Serial.print("rotations: ");
        // Serial.println(rotations);
        // Serial.println("[========================]");
        // prev_rotations = rotations;
    // }
    // if (rotations >= 10){
    //   Serial.println("DONE 10 ROTATIONS!");
    //   stop_motor(true);
    //   delay(10000);
    // }
}