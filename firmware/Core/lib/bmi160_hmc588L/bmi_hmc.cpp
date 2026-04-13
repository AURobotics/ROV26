#include "bmi_hmc.h"
#include "i2c.h"

BMI160_HMC_Data_t hNewIMU;
static struct bmi160_dev bmi160_sensor;
static uint32_t last_tick = 0;

// 1. I2C Wrapper Functions
int8_t bmi_i2c_read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len) {
    return (HAL_I2C_Mem_Read(&hi2c3, dev_addr << 1, reg_addr, 1, data, len, 100) == HAL_OK) ? 0 : -1;
}

int8_t bmi_i2c_write(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len) {
    return (HAL_I2C_Mem_Write(&hi2c3, dev_addr << 1, reg_addr, 1, data, len, 100) == HAL_OK) ? 0 : -1;
}

//IMU Reading Function
HAL_StatusTypeDef BMI160_HMC_Read_IMU(void) {
    struct bmi160_sensor_data acc, gyr;
    if (bmi160_get_sensor_data(BMI160_BOTH_ACCEL_AND_GYRO, &acc, &gyr, &bmi160_sensor) != BMI160_OK)
        return HAL_ERROR;

    hNewIMU.ax = acc.x * hNewIMU.accel_res;
    hNewIMU.ay = acc.y * hNewIMU.accel_res;
    hNewIMU.az = acc.z * hNewIMU.accel_res;

    hNewIMU.gx = (gyr.x - hNewIMU.gx_offset) * hNewIMU.gyro_res;
    hNewIMU.gy = (gyr.y - hNewIMU.gy_offset) * hNewIMU.gyro_res;
    hNewIMU.gz = (gyr.z - hNewIMU.gz_offset) * hNewIMU.gyro_res;

    return HAL_OK;
}

// Magnetometer Reading Function
HAL_StatusTypeDef BMI160_HMC_Read_Mag(void) {
    uint8_t raw[6], status;
    if (HAL_I2C_Mem_Read(&hi2c3, HMC5883L_ADDRESS, QMC_REG_STATUS,
                        1, &status, 1, 100) != HAL_OK)
        return HAL_ERROR;
    if (!(status & 0x01))
        return HAL_BUSY;

    if (HAL_I2C_Mem_Read(&hi2c3, HMC5883L_ADDRESS, QMC_REG_DATA_X_L, 1, raw, 6, 100) != HAL_OK)
        return HAL_ERROR;
   // HMC register order x_h , x_l , z_h ,z_l , y_h ,y_l
    int16_t mx = (int16_t)((raw[0] << 8) | raw[1]);
    int16_t mz = (int16_t)((raw[2] << 8) | raw[3]);
    int16_t my = (int16_t)((raw[4] << 8) | raw[5]);

    hNewIMU.mx = (mx - hNewIMU.mx_offset) * hNewIMU.mx_scale * hNewIMU.mag_res;
    hNewIMU.my = (my - hNewIMU.my_offset) * hNewIMU.my_scale * hNewIMU.mag_res;
    hNewIMU.mz = (mz - hNewIMU.mz_offset) * hNewIMU.mz_scale * hNewIMU.mag_res;

    return HAL_OK;
}

void BMI160_HMC_Update_Attitude(void) {

    if (BMI160_HMC_Read_IMU() != HAL_OK) {
        HAL_I2C_Init(&hi2c3);
        return;
    }

    // dt
    uint32_t now = HAL_GetTick();
    float dt = (float)(now - last_tick) / 1000.0f;
    last_tick = now;
    if (dt < 0.0005f || dt > 0.1f) dt = 0.005f;

    // Pitch & Roll from accelerometer (degrees)
    float pitch_acc = atan2f(-hNewIMU.ax,
                              sqrtf(hNewIMU.ay * hNewIMU.ay + hNewIMU.az * hNewIMU.az))
                      * RAD2DEG;
    float roll_acc  = atan2f(hNewIMU.ay, hNewIMU.az) * RAD2DEG;

    // Complementary filter
    hNewIMU.pitch = 0.98f * (hNewIMU.pitch + hNewIMU.gx * dt) + 0.02f * pitch_acc;
    hNewIMU.roll  = 0.98f * (hNewIMU.roll  + hNewIMU.gy * dt) + 0.02f * roll_acc;


    if (BMI160_HMC_Read_Mag() == HAL_OK) {
        float pitch_r = hNewIMU.pitch * DEG2RAD;
        float roll_r  = hNewIMU.roll  * DEG2RAD;

        float mx2 =  hNewIMU.mx * cosf(pitch_r)
                   + hNewIMU.my * sinf(roll_r) * sinf(pitch_r)
                   + hNewIMU.mz * cosf(roll_r) * sinf(pitch_r);

        float my2 =  hNewIMU.my * cosf(roll_r)
                   - hNewIMU.mz * sinf(roll_r);

        hNewIMU.yaw = atan2f(-my2, mx2) * RAD2DEG;
        if (hNewIMU.yaw < 0.0f) hNewIMU.yaw += 360.0f;
    }
}
// Calibration Functions
void BMI160_HMC_Calibrate_Gyro(void) {
    int32_t gx = 0, gy = 0, gz = 0;
    struct bmi160_sensor_data a, g;
    for(int i=0; i<200; i++) {
        bmi160_get_sensor_data(BMI160_GYRO_ONLY, &a, &g, &bmi160_sensor);
        gx += g.x;
        gy += g.y;
        gz += g.z;
        HAL_Delay(5);
    }
    hNewIMU.gx_offset = (int16_t)(gx / 200);
    hNewIMU.gy_offset = (int16_t)(gy / 200);
    hNewIMU.gz_offset = (int16_t)(gz / 200);
}

void BMI160_HMC_Calibrate_Mag(void) {
    
    hNewIMU.mx_scale = 1.0f;
    hNewIMU.my_scale = 1.0f;
    hNewIMU.mz_scale = 1.0f;
    hNewIMU.mx_offset = 0;
    hNewIMU.my_offset = 0;
    hNewIMU.mz_offset = 0;
}


int BMI160_HMC_Init(void) {
  BMI160_HMC_Calibrate_Mag();

    bmi160_sensor.id = BMI160_I2C_ADDR;
    bmi160_sensor.intf = BMI160_I2C_INTF;
    bmi160_sensor.read = bmi_i2c_read;
    bmi160_sensor.write = bmi_i2c_write;
    bmi160_sensor.delay_ms = HAL_Delay;

    if (bmi160_init(&bmi160_sensor) != BMI160_OK) return -1;

    bmi160_sensor.accel_cfg.range = BMI160_ACCEL_RANGE_16G;
    bmi160_sensor.accel_cfg.odr = BMI160_ACCEL_ODR_200HZ;
    bmi160_sensor.accel_cfg.bw = BMI160_ACCEL_BW_NORMAL_AVG4;
    bmi160_sensor.accel_cfg.power = BMI160_ACCEL_NORMAL_MODE;
    hNewIMU.accel_res = ACCEL_SCALE_16G;

    bmi160_sensor.gyro_cfg.range = BMI160_GYRO_RANGE_2000_DPS;
    bmi160_sensor.gyro_cfg.odr = BMI160_GYRO_ODR_200HZ;
    bmi160_sensor.gyro_cfg.bw = BMI160_GYRO_BW_NORMAL_MODE;
    bmi160_sensor.gyro_cfg.power = BMI160_GYRO_NORMAL_MODE;
    hNewIMU.gyro_res = GYRO_SCALE_2000DPS;

    if (bmi160_set_sens_conf(&bmi160_sensor) != BMI160_OK) return -2;

    uint8_t id = 0;
    // HAL_I2C_Mem_Read(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_ID_A, 1, &id, 1, 100);
    // if (id != 0x48) return -3;

    // uint8_t hmc_cfg[] = {0x78, 0x20, 0x00};
    // HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_CONFIG_A, 1, &hmc_cfg[0], 1, 100);
    // HAL_Delay(10);
    // HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_CONFIG_B, 1, &hmc_cfg[1], 1, 100);
    // HAL_Delay(10);
    // HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_MODE, 1, &hmc_cfg[2], 1, 100);
    // HAL_Delay(10);
    // hNewIMU.mag_res = MAG_SCALE_1_3GA;
    // return 0;
    uint8_t qmc_rst = 0x01;
    HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, QMC_REG_RESET, 1, &qmc_rst, 1, 100);
    HAL_Delay(10);

    // Mode: continuous, 200Hz, 8G range, 512 OSR
    uint8_t qmc_cfg = 0x1D;
    HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, QMC_REG_CONFIG1, 1, &qmc_cfg, 1, 100);
    HAL_Delay(10);

    hNewIMU.mag_res = 1.0f / 3000.0f;
}