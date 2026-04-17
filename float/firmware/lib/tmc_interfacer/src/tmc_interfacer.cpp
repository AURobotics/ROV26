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
    int result;
    if(SPS - floor(SPS) > 0.5)
        result = ceil(SPS);
    else
        result = floor(SPS);
    return result;

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
void TMC_interfacer::stop_motor(bool shutdown){
    // Serial.println("!");
    // if(shutdown){
    //     motor_stopped = true;
    // }
    // else if(!motor_stopped)
    //     return;
    int velocity = VACTUAL2SPS(driver.VACTUAL());
    if(velocity >= 1){
        velocity -= 1;
    }
    else if(velocity <= -1){
        velocity += 1;
    }
    driver.VACTUAL(SPS2VACTUAL(velocity));
    
}

void TMC_interfacer::disable_motor(){
    driver.toff(0);
    Serial.println("motor stopped successfully!");
    Serial.println("input any key to continue...");
    while(!(Serial.available() > 0)){
        delay(100);
    }
    Serial.read();
    driver.toff(5);
}

void TMC_interfacer::readSerialAndRespond() {
  if (Serial.available() > 0) {  // Check if data is available
    char receivedChar = Serial.read();  // Read a single character
    
    if (receivedChar == 'h') {  // Check if it matches 'h'
      stop_motor(true);
    }
  }
}


/* void TMC_interfacer::adjust_velocity(float target_position){
    
    if(target_position > this->max_distance)
        target_position = this->max_distance;
    else if(target_position < 0)
        target_position = 0;
    float current_position = ROTS2POS(this->rotations);
    float LHS = target_position - current_position; //left hand side of 2nd equation of motion (I am sorry if you are reading this)
    // Serial.print("LHS:");
    // Serial.println(LHS);

    int velocity_SPS = VACTUAL2SPS(driver.VACTUAL());
    float velocity = SPS2V(velocity_SPS); //velocity in mm/s
    float acc;

    if(LHS == 0) //target position is same as current position
        return;
    if(velocity >= 0)
        acc = -40; //assume decceleration is 40 mm/sec^2
    else
        acc = 40;

    float deceleration_time = (0 - velocity) / acc;
    float RHS = (velocity * deceleration_time) + (0.5 * acc * deceleration_time * deceleration_time);
    if(RHS < LHS){
        if(RHS >= 0) //forward distance needed > distance covered if we start stopping now, then accelerate 
            velocity_SPS += 1;
        else
            velocity_SPS -= 1; //backward distance needed > distance covered if we start stopping now, then accelerate
    }
    else if (RHS > 2 * LHS){ 
        if(RHS >= 0) //forward distance needed < 2 * distance covered if we start stopping now, then deccelerate with double the assummed rate
            velocity_SPS -= 2;
        else
            velocity_SPS += 2;
    }
    else{
        if(RHS >= 0)
            velocity_SPS -= 1;
        else
            velocity_SPS += 1;
    }
    // Serial.print("output SPS:");
    // Serial.println((int) velocity_SPS);
    // Serial.print("output VACTUAL:");
    // Serial.println(SPS2VACTUAL(velocity_SPS));

    set_velocity(velocity_SPS);
    // driver.VACTUAL(SPS2VACTUAL(velocity_SPS));
    delay(1);
}
*/

/*void TMC_interfacer::adjust_velocity(float target_position){
    if(target_position > this->max_distance)
        target_position = this->max_distance;
    else if(target_position < 0)
        target_position = 0;

    //get position
    float current_position = ROTS2POS(this->rotations);

    //get velocity
    int velocity_SPS = VACTUAL2SPS(driver.VACTUAL());
    float velocity = SPS2V(velocity_SPS); //velocity in mm/s
    float displacement = target_position - current_position;
    if(abs(displacement) < 0.1)
        return;
    float acc = - (velocity * velocity) / (2 * displacement);
    int SPS_modifier = 0;

    if(acc > 0 && acc < 0.01)
        SPS_modifier = 1;
    else if(acc < 0 && acc > -0.01)
        SPS_modifier = -1;
    else{
        float time = - velocity / acc;
        if(acc >= 0 && acc < 60)
            SPS_modifier = 1;
        else if(acc >= 0)
            SPS_modifier = 2;
        else if(acc < 0 && acc > -60)
            SPS_modifier = -1;
        else
            SPS_modifier = -2;

        if(time < 0){
            SPS_modifier = - SPS_modifier;
        }
    }
    set_velocity(velocity_SPS + SPS_modifier);
    delay(1);
}*/

/*void TMC_interfacer::adjust_velocity(float target_position){
    if(target_position > this->max_distance)
        target_position = this->max_distance;
    else if(target_position < 0)
        target_position = 0;

    //get position
    float current_position = ROTS2POS(this->rotations);
    float displacement = target_position - current_position;
    float acc = 40;
    int velocity_SPS = VACTUAL2SPS(driver.VACTUAL());
    float velocity = SPS2V(velocity_SPS); //velocity in mm/s
    if(velocity > 0 && displacement < 0){
        velocity_SPS -= 1;
        // Serial.println("REVERING DIRECTION");
    }
    else if(velocity < 0 && displacement > 0){
        velocity_SPS += 1;
        // Serial.println("REVERING DIRECTION");
    }
    else{
        float time = abs(velocity)/acc; //time to stop
        float stopping_displacement = (abs(velocity) * time) - (0.5 * acc * time * time);
        if(abs(stopping_displacement - abs(displacement)) < 0.1){
            stop_motor(true);
            return;
        }
        else if(stopping_displacement > abs(displacement)){
            if(velocity >= 0)
                velocity_SPS -= 1;
            else
                velocity_SPS += 1;
        }
        else{
            if(velocity >= 0)
                velocity_SPS += 1;
            else
                velocity_SPS -= 1;
        }
    }
    set_velocity(velocity_SPS);
}*/

void TMC_interfacer::adjust_velocity(float target_position){
    if(target_position > this->max_distance)
        target_position = this->max_distance;
    else if(target_position < 0)
        target_position = 0;

    //get position
    float current_position = ROTS2POS(this->rotations);
    float displacement = target_position - current_position;
    float acc = 40;
    int velocity_SPS = VACTUAL2SPS(driver.VACTUAL());
    float velocity = SPS2V(velocity_SPS); //velocity in mm/s
    if(abs(displacement) < 1)
        // if(velocity > 0)
        //     velocity_SPS -= 8;
        // else
        //     velocity_SPS += 8;
        stop_motor(true);
    else if(displacement > 0)
        velocity_SPS += 8;
    else
        velocity_SPS -= 8;
    set_velocity(velocity_SPS);

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
            rotations += (step_difference/(float)STEPS); 
        }
        else{
            rotations -= (step_difference/(float)STEPS); 
        }
        prev_sequencer = current_sequencer - remainder;
    }
    // if(!motor_stopped){ //make sure motor does not exceed the max rotations allowed
    //     if(going_forward && (max_rotations - rotations < 1.5)){
    //         stop_motor(true);
    //     }
    //     else if(!going_forward && (rotations < 1.5)){
    //         stop_motor(true);
    //     }
    // }
}

bool TMC_interfacer::set_velocity(int SPS){
    // bool safe_to_move = false;
    // if(motor_stopped){ 
    //     if((going_forward && velocity < 0) || (!going_forward && velocity > 0)){ //motor reached max position in one direction and now wants to switch
    //         safe_to_move = true;
    //         motor_stopped = false;
    //         going_forward = !going_forward;
    //     }
    // }
    // else{
    //     if((going_forward && velocity < 0) || (!going_forward && velocity > 0))
    //         going_forward = !going_forward;
    //     safe_to_move = true;
    // }
    // if(safe_to_move){
        if(SPS > this->max_motor_velocity)
            SPS = max_motor_velocity; //make sure to not exceed max motor velocity
        else if(SPS < -this->max_motor_velocity)
            SPS = - max_motor_velocity;
        if(SPS >= 0)
            going_forward = true;
        else
            going_forward = false;
        driver.VACTUAL(SPS2VACTUAL(SPS));

        return true;
    // }
    // else{
    //     return false;
    // }
}
