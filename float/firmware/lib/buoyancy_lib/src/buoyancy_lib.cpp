#include <buoyancy_lib.h>


TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS, MAX_MOTOR_VEL);
PID pid = PID(K_P, K_I, K_D, MAX_MOTOR_VEL * 500);

void buoyancy_setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN); 
  while(!Serial2){
    delay(1);
  }
  pid.set_point1 = 2.5;
  pid.set_point2 = 0;
  pid.current_set_point = pid.set_point1;
  driver.normal_setup(RMS_CURRENT, 0);
  pid.set_reference_time(millis());
}

void buoyancy_loop(float depth) {
  Serial.print("D:");
  Serial.println((int) (depth * 100));
  double velocity = pid.control_loop(depth) * 0.001;
  // Serial.print("V:");
  // Serial.println(velocity);
  driver.set_velocity(velocity);
  driver.measure_position();
  Serial.print("R:");
  Serial.println((int) driver.rotations);
  driver.readSerialAndRespond();
  driver.stop_motor(false);
}
