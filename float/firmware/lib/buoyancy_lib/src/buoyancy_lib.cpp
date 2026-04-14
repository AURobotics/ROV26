#include <buoyancy_lib.h>

void buoyancy_setup() {
  Serial.begin(9600);
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
  Serial.println((int) (depth * 100));
  double velocity = pid.control_loop(depth) * 0.001;
  Serial.print("velocity: ");
  Serial.println(velocity);
  driver.set_velocity(velocity);
  Serial.println("=======");
  delay(1);
  // driver.measure_position();
}

