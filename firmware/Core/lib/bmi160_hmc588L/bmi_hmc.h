#pragma once

#include "stm32f4xx_hal.h"
#include "bmi160.h"           
#include <cstdint>




extern  uint8_t GYRO_CALIB;
extern uint8_t MAG_CALIB;

#define DEG2RAD     0.0174532925f
#define RAD2DEG     57.2957795131f
#define G2MSS       9.80665f
#define PI         3.1415926535f

// HMC5883L I2C address and registers
// #define  HMC5883L_ADDRESS           (0x1E<<1)
// #define HMC5883L_REG_CONFIG_A       0x00
// #define HMC5883L_REG_CONFIG_B       0x01
// #define HMC5883L_REG_MODE           0x02
// #define HMC5883L_REG_DATA_X_H       0x03
// #define HMC5883L_REG_STATUS         0x09
// #define HMC5883L_REG_ID_A           0x0A

#define HMC5883L_ADDRESS      (0x0D << 1)   // QMC5883L address
#define QMC_REG_DATA_X_L       0x00         // X low byte أول
#define QMC_REG_STATUS         0x06
#define QMC_REG_CONFIG1        0x09
#define QMC_REG_CONFIG2        0x0A
#define QMC_REG_RESET          0x0B
// sensor scales
#define ACCEL_SCALE_16G             (16.0f / 32768.0f) * G2MSS
#define GYRO_SCALE_2000DPS          (2000.0f / 32768.0f)
#define MAG_SCALE_1_3GA             0.92f


struct BMI160_HMC_Data_t {
    uint8_t  gyro_calibration_done; 
    
    float    accel_res; 
    float    gyro_res;
    float    mag_res;

   // Gyro offsets in LSB (before scaling)
    int16_t  gx_offset, gy_offset, gz_offset;
    int16_t  mx_offset, my_offset, mz_offset;

    float accel_scale, gyro_scale, mag_scale;
    float    mx_scale, my_scale, mz_scale;

   // Public output 
    float ax, ay, az;   
    float gx, gy, gz;   
    float mx, my, mz;  

    float yaw, pitch, roll;
};


extern BMI160_HMC_Data_t hNewIMU;

int BMI160_HMC_Init(void);
HAL_StatusTypeDef BMI160_HMC_Read_IMU(void);
HAL_StatusTypeDef BMI160_HMC_Read_Mag(void);

void BMI160_HMC_Calibrate_Gyro(void);
void BMI160_HMC_Calibrate_Mag(void);
void BMI160_HMC_Update_Attitude(void);



