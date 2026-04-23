#include <tmc_interfacer.h>

TMC_interfacer::TMC_interfacer(int ms, float max_rotations, float max_motor_velocity){
    this->ms = ms;
    this->max_rotations = max_rotations;
    this->max_motor_velocity = max_motor_velocity;
    this->max_distance = max_rotations * 200;
}

int TMC_interfacer::VACTUAL2SPS(uint32_t VACTUAL){
    float SPS = ((int) VACTUAL) * this->oscillator_multiplier / this->ms;
    return (int) round(SPS);
}

uint32_t TMC_interfacer::SPS2VACTUAL(int steps){
    return steps * this->ms / this->oscillator_multiplier;
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


bool TMC_interfacer::adjust_velocity(int target_position, bool use_deadzone){
    if(target_position > this->max_distance)
        target_position = this->max_distance;
    else if(target_position < 0)
        target_position = 0;

    //get position
    int current_position = (int) (this->rotations * 200);
    int displacement = target_position - current_position;
    int velocity_SPS;
    // const int dead_zone = 50;
    int dead_zone;
    if(use_deadzone)
        dead_zone = 50;
    else
        dead_zone = 1;
    const int slow_zone = 100;
    // const int slow_velocity = 30;
    // const int fast_velocity = 100;
    const int slow_velocity = 20;
    const int fast_velocity = 45;
    if(abs(displacement) < dead_zone)
        velocity_SPS = 0;
    else if(displacement > 0)
        if(displacement <= slow_zone)
            velocity_SPS = slow_velocity;
        else
            velocity_SPS = fast_velocity;
    else
        if(displacement >= slow_zone)
            velocity_SPS = - slow_velocity; 
        else
            velocity_SPS = - fast_velocity;
    return set_velocity(velocity_SPS);
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
            // total_steps += step_difference;
            rotations += (step_difference/(float)STEPS); 
            prev_sequencer = (current_sequencer - remainder + 1024) % 1024;
        }
        else{
            total_steps -= step_difference;
            rotations -= (step_difference/(float)STEPS); 
            // prev_sequencer = (current_sequencer + remainder) % 1024;

        }
        // rotations = total_steps / (float) STEPS;

    }
}

bool TMC_interfacer::set_velocity(int SPS){
    bool result = true;
    if(SPS > this->max_motor_velocity)
        SPS = max_motor_velocity; //make sure to not exceed max motor velocity
    else if(SPS < -this->max_motor_velocity)
        SPS = - max_motor_velocity;

    if(SPS >= 0)
        going_forward = true;
    else
        going_forward = false;
    if((max_rotations - rotations < 1  && going_forward) || (rotations < 0.1 && !going_forward)){
        SPS = 0;
        result = false;
    }
    driver.VACTUAL(SPS2VACTUAL(SPS));
    return result;
}
