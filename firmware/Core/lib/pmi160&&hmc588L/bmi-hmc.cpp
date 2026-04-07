#include "bmi160_hmc5883l.h"
#include "i2c.h" 

int GYRO_CALIB = 1;
int MAG_CALIB  = 1;
BMI160_HMC_Data_t hNewIMU;
static struct bmi160_dev bmi160_sensor;


int8_t bmi_hmc_i2c_read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len) {
    if (HAL_I2C_Mem_Read(&hi2c3, dev_addr << 1, reg_addr, I2C_MEMADD_SIZE_8BIT, data, len, 500) != HAL_OK)
        return BMI160_E_COM_FAIL;
    return BMI160_OK;
}

int8_t bmi_hmc_i2c_write(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len) {
    if (HAL_I2C_Mem_Write(&hi2c3, dev_addr << 1, reg_addr, I2C_MEMADD_SIZE_8BIT, data, len, 500) != HAL_OK)
        return BMI160_E_COM_FAIL;
    return BMI160_OK;
}




int BMI160_HMC_Init(void) {
    bmi160_sensor.id = BMI160_I2C_ADDR;
    bmi160_sensor.interface = BMI160_I2C_INTF;
    bmi160_sensor.read = bmi_hmc_i2c_read;
    bmi160_sensor.write = bmi_hmc_i2c_write;
    bmi160_sensor.delay_ms = HAL_Delay;

    if (bmi160_init(&bmi160_sensor) != BMI160_OK) return -1;

   
    bmi160_sensor.accel_cfg.odr = BMI160_ACCEL_ODR_200HZ;
    bmi160_sensor.accel_cfg.range = BMI160_ACCEL_RANGE_16G;
    bmi160_sensor.accel_cfg.bw = BMI160_ACCEL_BW_NORMAL_AVG4;
    bmi160_sensor.accel_cfg.power = BMI160_ACCEL_NORMAL_MODE;
    hNewIMU.accel_res = ACCEL_SCALE_16G;

    bmi160_sensor.gyro_cfg.odr = BMI160_GYRO_ODR_200HZ;
    bmi160_sensor.gyro_cfg.range = BMI160_GYRO_RANGE_2000_DPS;
    bmi160_sensor.gyro_cfg.bw = BMI160_GYRO_BW_NORMAL_MODE;
    bmi160_sensor.gyro_cfg.power = BMI160_GYRO_NORMAL_MODE;
    hNewIMU.gyro_res = GYRO_SCALE_2000DPS;
    bmi160_set_sens_conf(&bmi160_sensor);


    uint8_t id = 0;
    HAL_I2C_Mem_Read(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_ID_A, 1, &id, 1, 100);
    if (id != 0x48) return -3;

    uint8_t hmc_cfg[] = {0x78, 0x20, 0x00}; // Config A, B, and Mode
    HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_CONFIG_A, 1, &hmc_cfg[0], 1, 100);
    HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_CONFIG_B, 1, &hmc_cfg[1], 1, 100);
    HAL_I2C_Mem_Write(&hi2c3, HMC5883L_ADDRESS, HMC5883L_REG_MODE, 1, &hmc_cfg[2], 1, 100);
    hNewIMU.mag_res = MAG_SCALE_1_3GA;

    if (GYRO_CALIB) BMI160_HMC_Calibrate_Gyro();
    if (MAG_CALIB) BMI160_HMC_Calibrate_Mag();

    return 0;
}

HAL_StatusTypeDef BMI160_HMC_Read_IMU(void) {
    struct bmi160_sensor_data acc, gyr;
    if (bmi160_get_sensor_data(BMI160_BOTH_ACCEL_AND_GYRO, &acc, &gyr, &bmi160_sensor) != BMI160_OK)
        return HAL_ERROR;
    hNewIMU.ax = a.x * hNewIMU.accel_res;
    hNewIMU.ay = a.y * hNewIMU.accel_res;
    hNewIMU.az = a.z * hNewIMU.accel_res;

    hNewIMU.gx = (g.x - hNewIMU.gx_off) * hNewIMU.gyro_res;
    hNewIMU.gy = (g.y - hNewIMU.gy_off) * hNewIMU.gyro_res;
    hNewIMU.gz = (g.z - hNewIMU.gz_off) * hNewIMU.gyro_res;

    return HAL_OK;
}
HAL_StatusTypeDef BMI160_HMC_Read_Mag(void) {
    uint8_t raw[6];
    if (HAL_I2C_Mem_Read(&hi2c3, NEW_HMC_ADDR, NEW_HMC_DATA_REG, 1, raw, 6, 100) != HAL_OK)
        return HAL_ERROR;

    int16_t mx = (int16_t)((raw[0] << 8) | raw[1]);
    int16_t mz = (int16_t)((raw[2] << 8) | raw[3]);
    int16_t my = (int16_t)((raw[4] << 8) | raw[5]);

    hNewIMU.mx = (mx - hNewIMU.mx_off) * hNewIMU.mx_scale * hNewIMU.mag_res;
    hNewIMU.my = (my - hNewIMU.my_off) * hNewIMU.my_scale * hNewIMU.mag_res;
    hNewIMU.mz = (mz - hNewIMU.mz_off) * hNewIMU.mz_scale * hNewIMU.mag_res;

    return HAL_OK;
}



void BMI160_HMC_Calibrate_Gyro(void) {
    int32_t sx = 0, sy = 0, sz = 0;
    struct bmi160_sensor_data dummy_a, g;
    for (int i = 0; i < 500; i++) {
        bmi160_get_sensor_data(BMI160_GYRO_ONLY, &dummy_a, &g, &bmi160_sensor);
        sx += g.x; sy += g.y; sz += g.z;
        HAL_Delay(2);
    }
    hNewIMU.gx_off = sx / 500;
    hNewIMU.gy_off = sy / 500;
    hNewIMU.gz_off = sz / 500;
}

void BMI160_HMC_Calibrate_Mag(void) {
   
}