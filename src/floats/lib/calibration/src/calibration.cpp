#include <calibration.h>

TMC2208Stepper driver = TMC2208Stepper(&Serial2, R_SENSE);


uint16_t micro_steps = 0;
float rotations = 0;
float prev_rotations = 0;
int current_sequencer = 0;
int prev_sequencer = 0;

void readSerialAndRespond(int ms) {
  if (Serial.available() > 0) {  // Check if data is available
    char receivedChar = Serial.read();  // Read a single character
    
    if (receivedChar == 'h') {  // Check if it matches 'h'
      stop_motor(ms, true);
    }
  }
}

void manual_ramp(int ms){
    int velocity = 10;
    while(true){
        while(Serial.available() <= 0)
            delay(10);
        char receivedChar = Serial.read();  // Read a single character
        if(receivedChar == 'u'){
            velocity += 5;
            driver.VACTUAL((uint32_t) (ms * velocity / 0.715));
            uint32_t vel = driver.VACTUAL();
            Serial.print("current vactual: ");
            Serial.println(vel);
            Serial.print("steps per second: ");
            Serial.println((vel / ms) * 0.715);
        }
        else if(receivedChar == 'd'){
            velocity -= 5;
            driver.VACTUAL((uint32_t) (ms * velocity / 0.715));
            uint32_t vel = driver.VACTUAL();
            Serial.print("current vactual: ");
            Serial.println(vel);
            Serial.print("steps per second: ");
            Serial.println((vel / ms) * 0.715);
        }
        else if(receivedChar == 'h'){
            stop_motor(ms, true);
        }
        else if(receivedChar == 'c'){
            break;
        }
    }
}

void stop_motor(int ms, bool shutdown){
    Serial.println("stopping motor...");
    uint32_t velocity = driver.VACTUAL();
    while(velocity >= 0){
        velocity -= 10;
        driver.VACTUAL(ms * velocity / 0.715);
        delay(100);
    }
    if(shutdown){
        driver.toff(0);
        Serial.println("motor stopped successfully!");
        Serial.println("input any key to continue...");
        while(!(Serial.available() > 0)){
            delay(100);
        }
    }
}

void calibration_setup(int rms_current, int ms){
    driver.begin(); 
    delay(500);
    driver.pdn_disable(true); 
    driver.toff(5); 
    driver.pwm_autoscale(true);
    driver.pwm_autograd(true);
    driver.I_scale_analog(false);
    driver.rms_current(rms_current); 
    driver.mstep_reg_select(true);
    driver.microsteps(ms);
    Serial.println("starting in 5 seconds: ");
    driver.toff(0); 
    delay(5000);
    Serial.println("started!");
    driver.toff(5); 
    driver.VACTUAL(8);
    delay(500); //wait for AT1 to end
    Serial.println("ramping up velocity...");
    // ramp_velocity(ms, 60);
    // delay(10000);
    // ramp_velocity(ms, 5);
    //manual ramp:
    manual_ramp(ms);
    Serial.print("reached max velocity, current value for pwm_scale_auto:");
    Serial.println(driver.pwm_scale_auto());
    Serial.print("velocity: ");
    Serial.println(driver.VACTUAL());
    //make sure spreadcycle did not get activated
    bool is_stealth = driver.stealth();
    if(!is_stealth){
        Serial.println("[WARNING]: operating in spreadcycle");
    }
    Serial.println("starting loop..");
}

void calibration_loop(int ms){
    uint16_t pwm_scale_auto_val = driver.pwm_scale_auto();
    uint8_t pwm_ofs = driver.pwm_ofs_auto();
    Serial.print("pwm_scale_auto: ");
    Serial.println(pwm_scale_auto_val);
    Serial.print("pwm_ofs_auto: ");
    Serial.println(pwm_ofs);
}