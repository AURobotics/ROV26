#include <buoyancy_lib.h>


TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS, MAX_MOTOR_VEL);
PID pid = PID(K_P, K_I, K_D, K_G, MAX_DISTANCE);
long start_time;
long finishing;
void buoyancy_setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN); 
  while(!Serial2){
    delay(1);
  }
  delay(500);
  while (Serial.available() <= 0) // wait for input to start
    delay(1);
  char temp = Serial.read();  // Read a single character

  pid.set_point1 = 2500;
  pid.set_point2 = 400;
  pid.current_set_point = pid.set_point1;

  driver.normal_setup(RMS_CURRENT, 0);
  pid.set_reference_time(millis());
  driver.set_velocity(400);
  start_time = millis();
}

void buoyancy_loop(float depth) {
  depth = depth * 1000; //m to mm

  double target_position = pid.control_loop(depth);
  // driver.adjust_velocity(target_position);
  // driver.measure_position();

  // driver.readSerialAndRespond();
  driver.stop_motor(false);

  Serial.print("D:");
  Serial.println((int) depth);
  Serial.print("V:");
  Serial.println(target_position);
  Serial.print("R:");
  Serial.println(driver.rotations);
  Serial.print("S:");
  int SPS = driver.VACTUAL2SPS(driver.driver.VACTUAL());
  Serial.println(SPS);
  if(SPS < 1){
    finishing = millis();
    while(true){
      Serial.print("time: ");
      Serial.println(finishing - start_time);
      delay(1);
    }
  }
  delay(1);
}
