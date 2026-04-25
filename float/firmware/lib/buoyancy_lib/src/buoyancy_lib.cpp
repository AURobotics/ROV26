#include <buoyancy_lib.h>

const int setpoints_num = 9;
// float setpoints[setpoints_num] = {2.5 - FLOAT_HEIGHT, 0.4, 2.5 - FLOAT_HEIGHT, 0.4, 0};
// float setpoints[setpoints_num] = {0.5, 0};

float setpoints[setpoints_num] = {2.5 - FLOAT_HEIGHT, 0, 0.4, 2.5 - FLOAT_HEIGHT, 0.4, 0, 0, 0, 0};

// float setpoints[setpoints_num] = {0.5, 0.1, 0.5, 0.1, 0};

TMC_interfacer driver = TMC_interfacer(MS, MAX_ROTATIONS, MAX_MOTOR_VEL);
PID pid = PID(K_P, K_I, K_D, MAX_DISTANCE, setpoints, setpoints_num);
bool buoyancy_setup(bool read_EEPROM)
{
  // Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(500);
  if (!driver.driver.GCONF())
    return false; // TODO
#ifdef ADJUST_POS
  driver.normal_setup(RMS_CURRENT, -15);
#else
  driver.normal_setup(RMS_CURRENT, 0);
#endif
  pid.set_reference_time(millis());

  return true;
}

void debugging_prints(float depth, int target_position)
{
  Serial.print("D:");
  Serial.println(depth);
  Serial.print("V:");
  Serial.println(target_position);
  Serial.print("R:");
  Serial.println(driver.rotations);
  Serial.print("S:");
  int SPS = driver.VACTUAL2SPS(driver.driver.VACTUAL());
  Serial.println(SPS);
  long curr = millis();
  Serial.print("t:");
  Serial.println(curr);
  Serial.print("dT:");
  if (pid.hold_position)
    Serial.println(curr - pid.Time);
  else
    Serial.println(-1);
}

void save_rotations()
{
#ifndef ADJUST_POS
  while (driver.rotations > 1)
  {
    driver.adjust_velocity(200, false);
    debugging_prints(0, 200);
    driver.measure_position();
  }
#endif
  driver.driver.VACTUAL(0);
  driver.driver.toff(0);
}

#ifdef ADJUST_POS
void buoyancy_loop(float depth)
{
  return;
}
#else
void buoyancy_loop(float depth)
{

  int target_position = pid.control_loop(depth) + 1300;
  driver.adjust_velocity(target_position, true);
  driver.measure_position();

  driver.readSerialAndRespond();
  debugging_prints(depth, target_position);
}
#endif

float getCurrentTarget()
{
  return pid.set_points[pid.current_setpoint_idx];
}

bool isComplete()
{
  return pid.sequence_done;
}
