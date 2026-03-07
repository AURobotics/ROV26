#pragma once

#include <cstdint>
// Data sheet link:
// https://cdn-shop.adafruit.com/datasheets/BST_BNO055_DS000_12.pdf

namespace  BNO055_Reg {

    // i2c address
    constexpr uint8_t BNO055_I2C_ADDR = 0x28; // if COM3 pin is connected to GND
    // constexpr uint8_t BNO055_I2C_ADDR = 0x29; // if COM3 pin is connected to 3.3V

    // read/write registers

    constexpr uint8_t MAG_RADIUS_MSB = 0x6A;
    constexpr uint8_t MAG_RADIUS_LSB = 0x69;
    constexpr uint8_t ACC_RADIUS_MSB = 0x68;
    constexpr uint8_t ACC_RADIUS_LSB = 0x67;

    constexpr uint8_t GYR_OFFSET_Z_MSB = 0x66;
    constexpr uint8_t GYR_OFFSET_Z_LSB = 0x65;
    constexpr uint8_t GYR_OFFSET_Y_MSB = 0x64;
    constexpr uint8_t GYR_OFFSET_Y_LSB = 0x63;
    constexpr uint8_t GYR_OFFSET_X_MSB = 0x62;
    constexpr uint8_t GYR_OFFSET_X_LSB = 0x61;

    constexpr uint8_t MAG_OFFSET_Z_MSB = 0x60;
    constexpr uint8_t MAG_OFFSET_Z_LSB = 0x5F;
    constexpr uint8_t MAG_OFFSET_Y_MSB = 0x5E;
    constexpr uint8_t MAG_OFFSET_Y_LSB = 0x5D;
    constexpr uint8_t MAG_OFFSET_X_MSB = 0x5C;
    constexpr uint8_t MAG_OFFSET_X_LSB = 0x5B;

    constexpr uint8_t ACC_OFFSET_Z_MSB = 0x5A;
    constexpr uint8_t ACC_OFFSET_Z_LSB = 0x59;
    constexpr uint8_t ACC_OFFSET_Y_MSB = 0x58;
    constexpr uint8_t ACC_OFFSET_Y_LSB = 0x57;
    constexpr uint8_t ACC_OFFSET_X_MSB = 0x56;
    constexpr uint8_t ACC_OFFSET_X_LSB = 0x55;

    constexpr  uint8_t AXiS_MAP_SIGN = 0x42;
    constexpr uint8_t AXiS_MAP_CONFIG = 0x41;

    constexpr uint8_t TEMP_SOURCE = 0x40;
    constexpr uint8_t SYS_TRIGGER = 0x3F;
    constexpr uint8_t PWR_MODE = 0x3E;
    constexpr uint8_t OPR_MODE = 0x3D;
    constexpr uint8_t UNIT_SEL = 0x3B;
    constexpr uint8_t SYS_CLK_STATUS = 0x38;


    // Read only registers

    constexpr uint8_t SYS_ERR = 0x3A;
    constexpr uint8_t SYS_STATUS = 0x39;
    constexpr uint8_t INT_STA = 0x37;
    constexpr uint8_t ST_RESULt = 0x36;
    constexpr uint8_t CALIB_STAT = 0x35;
    constexpr uint8_t TEMP = 0x34;

    // Gravity Vector Data
    constexpr uint8_t GRAV_DATA_Z_MSB = 0x33;
    constexpr uint8_t GRAV_DATA_Z_LSB = 0x32;
    constexpr uint8_t GRAV_DATA_Y_MSB = 0x31;
    constexpr uint8_t GRAV_DATA_Y_LSB = 0x30;
    constexpr uint8_t GRAV_DATA_X_MSB = 0x2F;
    constexpr uint8_t GRAV_DATA_X_LSB = 0x2E;

    // Linear Acceleration Data
    constexpr uint8_t LIA_DATA_Z_MSB = 0x2D;
    constexpr uint8_t LIA_DATA_Z_LSB = 0x2C;
    constexpr uint8_t LIA_DATA_Y_MSB = 0x2B;
    constexpr uint8_t LIA_DATA_Y_LSB = 0x2A;
    constexpr uint8_t LIA_DATA_X_MSB = 0x29;
    constexpr uint8_t LIA_DATA_X_LSB = 0x28;

    // Quaternion Data
    constexpr uint8_t QUA_DATA_z_MSB = 0x27;
    constexpr uint8_t QUA_DATA_z_LSB = 0x26;
    constexpr uint8_t QUA_DATA_y_MSB = 0x25;
    constexpr uint8_t QUA_DATA_y_LSB = 0x24;
    constexpr uint8_t QUA_DATA_x_MSB = 0x23;
    constexpr uint8_t QUA_DATA_x_LSB = 0x22;
    constexpr uint8_t QUA_DATA_w_MSB = 0x21;
    constexpr uint8_t QUA_DATA_w_LSB = 0x20;

    // Euler angles
    constexpr uint8_t EUL_Pitch_MSB = 0x1F;
    constexpr uint8_t EUL_Pitch_LSB = 0x1E;
    constexpr uint8_t EUL_Roll_MSB = 0x1D;
    constexpr uint8_t EUL_Roll_LSB = 0x1C;
    constexpr uint8_t EUL_Heading_MSB = 0x1B;
    constexpr uint8_t EUL_Heading_LSB = 0x1A;

    // Gyroscope Data
    constexpr uint8_t GYR_DATA_Z_MSB = 0x19;
    constexpr uint8_t GYR_DATA_Z_LSB = 0x18;
    constexpr uint8_t GYR_DATA_Y_MSB = 0x17;
    constexpr uint8_t GYR_DATA_Y_LSB = 0x16;
    constexpr uint8_t GYR_DATA_X_MSB = 0x15;
    constexpr uint8_t GYR_DATA_X_LSB = 0x14;

    // Magnetometer Data
    constexpr uint8_t MAG_DATA_Z_MSB = 0x13;
    constexpr uint8_t MAG_DATA_Z_LSB = 0x12;
    constexpr uint8_t MAG_DATA_Y_MSB = 0x11;
    constexpr uint8_t MAG_DATA_Y_LSB = 0x10;
    constexpr uint8_t MAG_DATA_X_MSB = 0x0F;
    constexpr uint8_t MAG_DATA_X_LSB = 0x0E;

    // Accelerometer Data
    constexpr uint8_t ACC_DATA_Z_MSB = 0x0D;
    constexpr uint8_t ACC_DATA_Z_LSB = 0x0C;
    constexpr uint8_t ACC_DATA_Y_MSB = 0x0B;
    constexpr uint8_t ACC_DATA_Y_LSB = 0x0A;
    constexpr uint8_t ACC_DATA_X_MSB = 0x09;
    constexpr uint8_t ACC_DATA_X_LSB = 0x08;

    constexpr uint8_t PAGE_ID = 0x07;
    constexpr uint8_t BL_Rev_ID = 0x06;
    constexpr uint8_t SW_REV_ID_MSB = 0x05;
    constexpr uint8_t SW_REV_ID_LSB = 0x04;
    constexpr uint8_t GYR_ID = 0x03;
    constexpr uint8_t MAG_ID = 0x02;
    constexpr uint8_t ACC_ID = 0x01;
    constexpr uint8_t CHIP_ID = 0x00;

}

