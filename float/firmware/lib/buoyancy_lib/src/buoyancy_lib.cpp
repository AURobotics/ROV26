#include <buoyancy_lib.h>
#include <EEPROM.h>

const int setpoints_num = 5;
float setpoints[setpoints_num] = {2.5 - FLOAT_HEIGHT, 0.4, 2.5 - FLOAT_HEIGHT, 0.4, 0};

TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS, MAX_MOTOR_VEL);
PID pid = PID(K_P, K_I, K_D, MAX_DISTANCE, setpoints, setpoints_num);
bool buoyancy_setup(bool read_EEPROM)
{
  // Serial.begin(115200);
  bool res = EEPROM.begin(EEPROM_SIZE);
  if (read_EEPROM)
  {
    float stored_rotations = EEPROM.readFloat(0);
    driver.rotations = stored_rotations;
  }
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN);
  while (!Serial2)
  {
    delay(1);
  }
  delay(500);

  while (Serial.available() <= 0) // wait for input to start
    delay(1);
  char temp = Serial.read(); // Read a single character
  if (temp == 'n')
    driver.rotations = 0;
  driver.normal_setup(RMS_CURRENT, 0);
  pid.set_reference_time(millis());

  return res;
}

void save_rotations()
{
  EEPROM.writeFloat(0, driver.rotations);
  EEPROM.writeBool(sizeof(float), true);
  EEPROM.commit();
}

void buoyancy_loop(float depth)
{

  int target_position = pid.control_loop(depth) + 1300;
  driver.adjust_velocity(target_position);
  driver.measure_position();

  driver.readSerialAndRespond();

  if (Serial.available() > 0)
  {                                    // Check if data is available
    char receivedChar = Serial.read(); // Read a single character
    if (receivedChar == 's')
    { // Check if it matches 'h'
      save_rotations();
      driver.driver.VACTUAL(0);
      delay(10000);
    }
    else if (receivedChar == 'h')
    {
      driver.driver.toff(0);
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
  Serial.print("T:");
  if (pid.hold_position)
    Serial.println(millis() - pid.Time);
  else
    Serial.println(-1);
}
