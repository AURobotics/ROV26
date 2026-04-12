#include <global_functions.h>
#include <control_lib.h>
#define MS 256
#define RMS_CURRENT 800
#define K_P 0.086
#define K_I 0.00879
#define K_D 0.187
#define MAX_MOTOR_VEL 10000
#define MAX_DISTANCE 10
#define MAX_ROTATIONS 12

TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS);
PID pid = PID(K_P, K_I, K_D, MAX_MOTOR_VEL);

void setup() {
  
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN); 
  while(!Serial2){
    delay(1);
  }
  pid.set_point = 2.5;
  driver.normal_setup(RMS_CURRENT, 0);
}

void loop() {
  float height = get_height(); //from pressure sensor
  double velocity = pid.control_loop();
  driver.set_velocity(velocity);
  driver.measure_position();
}

