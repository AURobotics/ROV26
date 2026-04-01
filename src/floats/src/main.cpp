#include <global_functions.h>
// #include <control_lib.h>
// #include <position_test.h>
//stepper motor microsteps
#define MS 256
#define RMS_CURRENT 1300
#define K_P 0.086
#define K_I 0.00879
#define K_D 0.187
#define MAX_MOTOR_VEL 10
#define MAX_DISTANCE 10

TMC_interfacer driver = TMC_interfacer(MS);

void setup() {
  
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN); 
  while(!Serial2){
    delay(1);
  }
  Serial.begin(9600); 
  delay(500); 
  Serial.print("TMC interfacer created with ms: ");
  Serial.println(driver.ms);
  driver.normal_setup(RMS_CURRENT, 25);
  driver.manual_ramp();
  // normal_setup(RMS_CURRENT, MS);
}

void loop() {  
  driver.measure_position();
  delay(20);
  driver.readSerialAndRespond();
}
