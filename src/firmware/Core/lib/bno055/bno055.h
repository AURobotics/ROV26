#pragma once

#include "i2c_wrapper.h"

struct CalibrationData {
  uint16_t mag_radius;
  uint16_t acc_radius;
  uint16_t gyr_offset_x, gyr_offset_y, gyr_offset_z;
  uint16_t mag_offset_x, mag_offset_y, mag_offset_z;
  uint16_t acc_offset_x, acc_offset_y, acc_offset_z;
  uint8_t calibration_status;
};

struct euler_angles {
  float yaw;
  float pitch;
  float roll;
};

struct body_rates {
  float z; //angular yaw
  float y; //angular pitch
  float x; //angular roll
};

struct vec_3 {
    float vec[3];
    float& x() { return vec[0]; }
    float& y() { return vec[1]; }
    float& z() { return vec[2]; }
    const float& x() const { return vec[0]; }
    const float& y() const { return vec[1]; }
    const float& z() const { return vec[2]; }
};

class BNO055 {
public:
    BNO055() = default;
private:
    I2C *i2c;

public:
  explicit BNO055(I2C *i2c_hal);
  void calibration();
  void init();
  static void saveCalibration(const CalibrationData &data);
  static bool loadCalibration(CalibrationData &data);
  vec_3 get_body_rates();
  vec_3 get_euler_angles() const;
};


