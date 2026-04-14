#include <tmc_interfacer.h>
#include <control_lib.h>
#define MS 256
#define RMS_CURRENT 800
#define K_P 0.086
#define K_I 0.00879 / 7
#define K_D 0.187
#define MAX_MOTOR_VEL 4 * POWER_SCREW_SIZE //basically, 4 rotations per second
// #define MAX_MOTOR_VEL 100000
#define MAX_DISTANCE 10
#define MAX_ROTATIONS 12

TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS, MAX_MOTOR_VEL);
PID pid = PID(K_P, K_I, K_D, MAX_MOTOR_VEL);

void setup() {
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

void loop() {
  double height = getDepth(); //from pressure sensor
  Serial.println((int) (height * 100));
  double velocity = pid.control_loop(height) * 0.001;
  Serial.print("velocity: ");
  Serial.println(velocity);
  driver.set_velocity(velocity);
  Serial.println("=======");
  delay(1);
  // driver.measure_position();
}

