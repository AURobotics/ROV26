#include <global_functions.h>

//not important
// void ramp_velocity(int ms, uint32_t target_velocity){
//     uint32_t velocity = driver.VACTUAL() / ms * 0.715;
//     int step;
//     bool accelerate;
//     if(target_velocity > velocity){
//        step = 10;
//         accelerate = true;
//     }
//     else if(target_velocity < velocity){
//         step = -10;
//         accelerate = false;
//     }
//     else
//         return;
    
//     while((accelerate && velocity < target_velocity) || (!accelerate && velocity > target_velocity)){
//         velocity += step;
//         driver.VACTUAL((uint32_t) (ms * velocity / 0.715));
//         Serial.print("current vactual: ");
//             Serial.println(driver.VACTUAL());
//         if (Serial.available() > 0) {  // Check if data is available
//             char receivedChar = Serial.read();  // Read a single character
    
//             if (receivedChar == 'h') {  // Check if it matches 'h'
//                 driver.toff(0);
//                 delay(90000);
//             }
//         } 
//         delay(200);
//     }
// }

TMC_interfacer::TMC_interfacer(int ms){
    this->ms = ms;
}

float TMC_interfacer::VACTUAL2SPS(uint32_t VACTUAL){
    return VACTUAL / this->ms * this->oscillator_multiplier;
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
    if(shutdown){
        driver.toff(0);
        Serial.println("motor stopped successfully!");
        Serial.println("input any key to continue...");
        while(!(Serial.available() > 0)){
            delay(100);
        }
        Serial.read();
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
    Serial.print("using MS = ");
    Serial.println(driver.microsteps());
    Serial.println("starting in 5 seconds: ");
    driver.toff(0); 
    delay(5000);
    Serial.println("started!");
    driver.toff(5); 
    driver.VACTUAL(SPS2VACTUAL(steps_per_second));
    // driver.VACTUAL(50 * this->ms / this->oscillator_multiplier);
}

void TMC_interfacer::manual_ramp(){
    int velocity = 10;
    while(true){
        while(Serial.available() <= 0)
            delay(10);
        char receivedChar = Serial.read();  // Read a single character
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

void TMC_interfacer::measure_position(){
    //TODO HANDLE BACKWORD ROTATION COUNTING
    //TODO HANDLE POSITION ACCURACY (about 30 degree error per rotation)
    current_sequencer = driver.MSCNT();
    int sequence_difference = current_sequencer - prev_sequencer;
    if(sequence_difference < 0){
        sequence_difference += 1023; //1023 -> maximum value MSCNT can hold
    }
    int step_difference = sequence_difference / 256; //every 256, a step has been made
    if(sequence_difference >= 1){
        rotations += (1/(float)STEPS) * step_difference; 
        prev_sequencer = current_sequencer;
    }
    // Serial.println(current_sequencer);
    if(rotations - prev_rotations >= 1){
        Serial.print("rotations: ");
        Serial.println(rotations);
        Serial.println("[========================]");
        prev_rotations = rotations;
    }
    if (rotations >= 10){
      Serial.println("DONE 10 ROTATIONS!");
      driver.VACTUAL(0);
      delay(10000);
    }
}