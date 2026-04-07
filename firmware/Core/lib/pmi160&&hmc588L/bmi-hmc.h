#ifndef BMI160_HMC5883L_H_
#define BMI160_HMC5883L_H_

#include "stm32f4xx_hal.h"
#include "bmi160.h"           
#include <cstdint>


extern BMI160_HMC_Data_t hNewIMU;
extern int GYRO_CALIB;
extern int MAG_CALIB;


#define RAD2DEG     57.2957795131f
#define G2MSS       9.80665f
#define PI          3.1415926535f

// ─── HMC5883L Register Map ──────────────────────────────────────────
#define HMC5883L_ADDRESS            (0x1E << 1)
#define HMC5883L_REG_CONFIG_A       0x00
#define HMC5883L_REG_CONFIG_B       0x01
#define HMC5883L_REG_MODE           0x02
#define HMC5883L_REG_DATA_X_H       0x03
#define HMC5883L_REG_STATUS         0x09
#define HMC5883L_REG_ID_A           0x0A


// Accel: ±16g
#define ACCEL_SCALE_16G             (16.0f / 32768.0f) * G2MSS
// Gyro: ±2000dps
#define GYRO_SCALE_2000DPS          (2000.0f / 32768.0f) * (PI / 180.0f)
// Mag: Sensitivity 
#define MAG_SCALE_1_3GA             0.92f


struct BMI160_HMC_Data_t {
    uint8_t  gyro_calibration_done;
    
    float    accel_res; 
    float    gyro_res;
    float    mag_res;

   // Gyro offsets in LSB (before scaling)
    int16_t  gx_offset, gy_offset, gz_offset;
    int16_t  mx_offset, my_offset, mz_offset;
    float    mx_scale, my_scale, mz_scale;

   // Public output 
    float ax, ay, az;   
    float gx, gy, gz;   
    float mx, my, mz;  
};



int BMI160_HMC_Init(void);
HAL_StatusTypeDef BMI160_HMC_Read_IMU(void);
HAL_StatusTypeDef BMI160_HMC_Read_Mag(void);
void BMI160_HMC_Calibrate_Gyro(void);
void BMI160_HMC_Calibrate_Mag(void);


int8_t user_i2c_read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len);
int8_t user_i2c_write(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len);
void user_delay_ms(uint32_t period);

#endif