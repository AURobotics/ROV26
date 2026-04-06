// #include <global_functions.h>
#include <control_lib.h>
#define MS 256
#define RMS_CURRENT 500
#define K_P 0.086
#define K_I 0.00879
#define K_D 0.187
#define MAX_MOTOR_VEL 10000
#define MAX_DISTANCE 10

// TMC_interfacer driver = TMC_interfacer(MS);

// void setup() {
  
//   Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN); 
//   while(!Serial2){
//     delay(1);
//   }
//   pinMode(STEP_PIN, OUTPUT);  
//   Serial.begin(9600); 
//   delay(500); 
//   Serial.print("TMC interfacer created with ms: ");
//   Serial.println(driver.ms);
//   driver.normal_setup(RMS_CURRENT, 0);
//   driver.calibrate();
//   // driver.step_dir_ramp();
//   driver.manual_ramp();
//   // driver.single_step();
//   // normal_setup(RMS_CURRENT, MS);
// }

// void loop() {  
//   // driver.measure_position();
//   driver.calibration_loop();
//   delay(60);
//   driver.readSerialAndRespond();
// }

PID pid = PID(K_P, K_I, K_D, MAX_MOTOR_VEL);
void setup(){
  Serial.begin(9600);
  delay(100);
  Serial.println(get_height());
}

void loop(){
  delay(1000);
}