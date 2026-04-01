#include <position_test.h>

TMC2208Stepper driver = TMC2208Stepper(&Serial2, R_SENSE);


void normal_setup(int rms_current, int ms){
    driver.begin(); 
    delay(500);
    driver.pdn_disable(true); 
    driver.toff(5); 
    driver.pwm_autoscale(true); 
    driver.I_scale_analog(false);
    driver.rms_current(rms_current); 
    driver.mstep_reg_select(true);
    driver.microsteps(ms); 
    Serial.println("starting in 5 seconds: ");
    driver.toff(0); 
    delay(5000);
    Serial.println("started!");
    driver.toff(5); 
    int velocity = 50;
    driver.VACTUAL((uint32_t) (ms * velocity / 0.715));
    while(true){
        while(Serial.available() <= 0)
            delay(10);
        char receivedChar = Serial.read();  // Read a single character
        if(receivedChar == 'u'){
            velocity += 10;
            driver.VACTUAL((uint32_t) (ms * velocity / 0.715));
            uint32_t vel = driver.VACTUAL();
            Serial.print("current vactual: ");
            Serial.println(vel);
            Serial.print("steps per second: ");
            Serial.println((vel / ms) * 0.715);
        }
        else if(receivedChar == 'd'){
            velocity -= 10;
            driver.VACTUAL((uint32_t) (ms * velocity / 0.715));
            uint32_t vel = driver.VACTUAL();
            Serial.print("current vactual: ");
            Serial.println(vel);
            Serial.print("steps per second: ");
            Serial.println((vel / ms) * 0.715);
        }
        else if(receivedChar == 'h'){
            Serial.println("stopping...");
            driver.toff(0);
            delay(100000);
        }
    }
}

void readSerialAndRespond() {
  if (Serial.available() > 0) {  // Check if data is available
    char receivedChar = Serial.read();  // Read a single character
    
    if (receivedChar == 'h') {  // Check if it matches 'h'
      driver.toff(0);
      Serial.println("stopped the motor!");
      delay(90000);
    }
  }
}