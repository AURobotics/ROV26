#include <buoyancy_lib.h>
#include <EEPROM.h>

TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS, MAX_MOTOR_VEL);
PID pid = PID(K_P, K_I, K_D, MAX_DISTANCE);
void buoyancy_setup() {
  Serial.begin(115200);
  EEPROM.begin(EEPROM_SIZE);
  bool rotations_stored = EEPROM.readBool(sizeof(float));
  if(rotations_stored){
    float stored_rotations = EEPROM.readFloat(0);
    driver.rotations = stored_rotations;
  }
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN); 
  while(!Serial2){
    delay(1);
  }
  delay(500);
  
  while (Serial.available() <= 0) // wait for input to start
    delay(1);
  char temp = Serial.read();  // Read a single character
  if(temp == 'n')
    driver.rotations = 0;
  
  pid.set_point1 = 2.5 - FLOAT_HEIGHT;
  pid.set_point2 = 0.4;
  pid.current_set_point = pid.set_point1;

  driver.normal_setup(RMS_CURRENT, 0);
  pid.set_reference_time(millis());
}

void save_rotations(){
  EEPROM.writeFloat(0, driver.rotations);
  EEPROM.writeBool(sizeof(float), true);
  EEPROM.commit();
}

void buoyancy_loop(float depth) {

  int target_position = pid.control_loop(depth) + 1300;
  driver.adjust_velocity(target_position);
  driver.measure_position();

  // driver.readSerialAndRespond();
  // driver.stop_motor(false);
  if (Serial.available() > 0) {  // Check if data is available
    char receivedChar = Serial.read();  // Read a single character
    
    if (receivedChar == 's') {  // Check if it matches 'h'
      save_rotations();
      driver.driver.VACTUAL(0);
      delay(10000);
    }
  }
  Serial.print("D:");
  Serial.println(depth);
  Serial.print("V:");
  Serial.println(target_position);
  Serial.print("R:");
  Serial.println(driver.rotations);
  Serial.print("S:");
  int SPS = driver.VACTUAL2SPS(driver.driver.VACTUAL());
  Serial.println(SPS);
  // Serial.print("time: ");
  // Serial.println(millis());
  // int SPS = driver.VACTUAL2SPS(driver.driver.VACTUAL());
  // Serial.println(SPS);
  // if(SPS < 1){
  //   finishing = millis();
  //   while(true){
  //     Serial.print("time: ");
  //     Serial.println(finishing - start_time);
  //     delay(1);
  //   }
  // }
  // delay(1);
}
