#include <tmc_interfacer.h>

TMC_interfacer::TMC_interfacer(int ms, float max_rotations, float max_motor_velocity){
    this->ms = ms;
    this->max_rotations = max_rotations;
    this->max_motor_velocity = V2SPS(max_motor_velocity);
    this->max_distance = ROTS2POS(max_rotations);
}

int TMC_interfacer::VACTUAL2SPS(uint32_t VACTUAL){
    float SPS = ((int) VACTUAL) * this->oscillator_multiplier / this->ms;
    return (int) round(SPS);
}

uint32_t TMC_interfacer::SPS2VACTUAL(int steps){
    // Serial.print("SPS2VACTUAL INPUT:");
    // Serial.println(steps);
    return steps * this->ms / this->oscillator_multiplier;
}

int TMC_interfacer::V2SPS(float velocity){
    float SPS = (velocity / POWER_SCREW_SIZE) * STEPS;
    return (int) round(SPS);

}
float TMC_interfacer::SPS2V(int SPS){
    return ((float) SPS / STEPS) * POWER_SCREW_SIZE;
}

float TMC_interfacer::POS2ROTS(float pos){
    return pos / POWER_SCREW_SIZE;
}

float TMC_interfacer::ROTS2POS(float rotations){
    return rotations * POWER_SCREW_SIZE;
}
void TMC_interfacer::stop_motor(){
    int velocity = VACTUAL2SPS(driver.VACTUAL());
    if(velocity > fast_decceleration_threshold)
        velocity -= fast_deceleration_step;
    else if(velocity < - fast_decceleration_threshold)
        velocity += fast_deceleration_step;
    else if(velocity >= 1){
        velocity -= 1;
    }
    else if(velocity <= -1){
        velocity += 1;
    }
    driver.VACTUAL(SPS2VACTUAL(velocity));
    
}


void TMC_interfacer::readSerialAndRespond() {
  if (Serial.available() > 0) {  // Check if data is available
    char receivedChar = Serial.read();  // Read a single character
    
    if (receivedChar == 'h') {  // Check if it matches 'h'
      stop_motor(); //FIX FOR DEBUGGING
    }
  }
}


void TMC_interfacer::adjust_velocity(float target_position){
    if(target_position > this->max_distance)
        target_position = this->max_distance;
    else if(target_position < 0)
        target_position = 0;

    //get position
    float current_position = ROTS2POS(this->rotations);
    float displacement = target_position - current_position;
    int velocity_SPS = VACTUAL2SPS(driver.VACTUAL());
    float velocity = SPS2V(velocity_SPS); //velocity in mm/s
    if(abs(displacement) < 2)
        stop_motor();
    else if(displacement > 0)
        velocity_SPS += 8;
    else
        velocity_SPS -= 8;
    set_velocity(velocity_SPS);

}

void TMC_interfacer::adjust_velocity_STEPDIR(float target_position){
    bool forward = true;
    bool backward = !forward;
    bool direction;
    float current_position = ROTS2POS(this->rotations);
    float displacement = target_position - current_position;
    if(displacement < 1 || displacement < -1)
        return;
    if(displacement >= 0)
        direction = forward;
    else
        direction = backward;
    
}
void TMC_interfacer::normal_setup(int rms_current, int steps_per_second){
    driver.begin(); 
    delay(500);
    driver.pdn_disable(true); 
    driver.pwm_autoscale(true); 
    driver.I_scale_analog(false);
    driver.rms_current(rms_current); 
    driver.mstep_reg_select(true);
    driver.microsteps(this->ms);
    if(this->ms == 0)
        this->ms += 1;
    driver.VACTUAL(SPS2VACTUAL(steps_per_second));
}

void TMC_interfacer::STEPDIR_setup(int rms_current){
    driver.begin(); 
    delay(500);
    driver.pdn_disable(true); 
    driver.pwm_autoscale(true); 
    driver.I_scale_analog(false);
    driver.rms_current(rms_current); 
    driver.mstep_reg_select(true);
    driver.microsteps(this->ms);
    if(this->ms == 0)
        this->ms += 1;
    driver.VACTUAL(0);
    pinMode(STEP_PIN, OUTPUT);
    pinMode(DIR_PIN, OUTPUT);
    digitalWrite(DIR_PIN, true);
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
}

bool TMC_interfacer::set_velocity(int SPS){
    if(SPS > this->max_motor_velocity)
        SPS = max_motor_velocity; //make sure to not exceed max motor velocity
    else if(SPS < -this->max_motor_velocity)
        SPS = - max_motor_velocity;

    if(SPS >= 0)
        going_forward = true;
    else
        going_forward = false;
    if((max_rotations - rotations < 1  && going_forward) || (rotations < 1 && !going_forward)){
        stop_motor();
        return false;
    }
    driver.VACTUAL(SPS2VACTUAL(SPS));
    return true;
}
