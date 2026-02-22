#include "bno055.h"
#include "bno055_reg_map.h"
#include "stm32f4xx_hal.h"

using namespace BNO055_Reg;

BNO055::BNO055(I2C *i2c_hal) {
    i2c = i2c_hal;
}

void BNO055::calibration() {
    i2c->write_reg(BNO055_I2C_ADDR, OPR_MODE, 0x0C); // NDOF fusion mode
    i2c->write_reg(BNO055_I2C_ADDR, UNIT_SEL, 0x00);
    HAL_Delay(30);


    uint8_t calib_status{};
    i2c->read_reg(BNO055_I2C_ADDR, CALIB_STAT, &calib_status);
    // ReSharper disable once CppDFALoopConditionNotUpdated
    while (calib_status != 0xFF) {
        HAL_Delay(500);
        i2c->read_reg(BNO055_I2C_ADDR, CALIB_STAT, &calib_status);
    }

    i2c->write_reg(BNO055_I2C_ADDR, OPR_MODE, 0x00); // back to config mode
    HAL_Delay(30);

    CalibrationData data{};

    i2c->read_2reg(BNO055_I2C_ADDR, MAG_RADIUS_MSB, MAG_RADIUS_LSB, &data.mag_radius);
    i2c->read_2reg(BNO055_I2C_ADDR, ACC_RADIUS_MSB, ACC_RADIUS_LSB, &data.acc_radius);

    i2c->read_2reg(BNO055_I2C_ADDR, GYR_OFFSET_Z_MSB, GYR_OFFSET_Z_LSB, &data.gyr_offset_z);
    i2c->read_2reg(BNO055_I2C_ADDR, GYR_OFFSET_Y_MSB, GYR_OFFSET_Y_LSB, &data.gyr_offset_y);
    i2c->read_2reg(BNO055_I2C_ADDR, GYR_OFFSET_X_MSB, GYR_OFFSET_X_LSB, &data.gyr_offset_x);

    i2c->read_2reg(BNO055_I2C_ADDR, MAG_OFFSET_Z_MSB, MAG_OFFSET_Z_LSB, &data.mag_offset_z);
    i2c->read_2reg(BNO055_I2C_ADDR, MAG_OFFSET_Y_MSB, MAG_OFFSET_Y_LSB, &data.mag_offset_y);
    i2c->read_2reg(BNO055_I2C_ADDR, MAG_OFFSET_X_MSB, MAG_OFFSET_X_LSB, &data.mag_offset_x);

    i2c->read_2reg(BNO055_I2C_ADDR, ACC_OFFSET_Z_MSB, ACC_OFFSET_Z_LSB, &data.acc_offset_z);
    i2c->read_2reg(BNO055_I2C_ADDR, ACC_OFFSET_Y_MSB, ACC_OFFSET_Y_LSB, &data.acc_offset_y);
    i2c->read_2reg(BNO055_I2C_ADDR, ACC_OFFSET_X_MSB, ACC_OFFSET_X_LSB, &data.acc_offset_x);

    data.calibration_status = 0x01;

    saveCalibration(data);
    HAL_Delay(30);
}

void BNO055::init() {
    CalibrationData data;
    if (!loadCalibration(data)) {
        calibration();
        loadCalibration(data);
    }

    i2c->write_reg(BNO055_I2C_ADDR, OPR_MODE, 0x00); // back to config mode
    HAL_Delay(30);
    i2c->write_reg(BNO055_I2C_ADDR, UNIT_SEL, 0x00);

    i2c->write_2reg(BNO055_I2C_ADDR, MAG_RADIUS_MSB, MAG_RADIUS_LSB, data.mag_radius);
    i2c->write_2reg(BNO055_I2C_ADDR, ACC_RADIUS_MSB, ACC_RADIUS_LSB, data.acc_radius);

    i2c->write_2reg(BNO055_I2C_ADDR, GYR_OFFSET_Z_MSB, GYR_OFFSET_Z_LSB, data.gyr_offset_z);
    i2c->write_2reg(BNO055_I2C_ADDR, GYR_OFFSET_Y_MSB, GYR_OFFSET_Y_LSB, data.gyr_offset_y);
    i2c->write_2reg(BNO055_I2C_ADDR, GYR_OFFSET_X_MSB, GYR_OFFSET_X_LSB, data.gyr_offset_x);

    i2c->write_2reg(BNO055_I2C_ADDR, MAG_OFFSET_Z_MSB, MAG_OFFSET_Z_LSB, data.mag_offset_z);
    i2c->write_2reg(BNO055_I2C_ADDR, MAG_OFFSET_Y_MSB, MAG_OFFSET_Y_LSB, data.mag_offset_y);
    i2c->write_2reg(BNO055_I2C_ADDR, MAG_OFFSET_X_MSB, MAG_OFFSET_X_LSB, data.mag_offset_x);

    i2c->write_2reg(BNO055_I2C_ADDR, ACC_OFFSET_Z_MSB, ACC_OFFSET_Z_LSB, data.acc_offset_z);
    i2c->write_2reg(BNO055_I2C_ADDR, ACC_OFFSET_Y_MSB, ACC_OFFSET_Y_LSB, data.acc_offset_y);
    i2c->write_2reg(BNO055_I2C_ADDR, ACC_OFFSET_X_MSB, ACC_OFFSET_X_LSB, data.acc_offset_x);

    i2c->write_reg(BNO055_I2C_ADDR, OPR_MODE, 0x0C); // NDOF fusion mode
    HAL_Delay(10);
}

body_rates BNO055::get_body_rates() {
    body_rates data;
    i2c->read_2reg(BNO055_I2C_ADDR, GYR_DATA_Z_MSB, GYR_DATA_Z_LSB, (uint16_t*)&data.z);
    i2c->read_2reg(BNO055_I2C_ADDR, GYR_DATA_Y_MSB, GYR_DATA_Y_LSB, (uint16_t*)&data.y);
    i2c->read_2reg(BNO055_I2C_ADDR, GYR_DATA_X_MSB, GYR_DATA_X_LSB, (uint16_t*)&data.x);

    data.z = data.z / 16.0;
    data.y = data.y / 16.0;
    data.x = data.x / 16.0;

    return data;
}

euler_angles BNO055::get_euler_angles() {
    euler_angles data;
    i2c->read_2reg(BNO055_I2C_ADDR, EUL_Heading_MSB, EUL_Heading_LSB, (uint16_t*)&data.yaw);
    i2c->read_2reg(BNO055_I2C_ADDR, EUL_Pitch_MSB, EUL_Pitch_LSB, (uint16_t*)&data.pitch);
    i2c->read_2reg(BNO055_I2C_ADDR, EUL_Roll_MSB, EUL_Roll_LSB, (uint16_t*)&data.roll);

    data.yaw = data.yaw / 16.0;
    data.pitch = data.pitch / 16.0;
    data.roll = data.roll / 16.0;

    return data;
}

void BNO055::saveCalibration(CalibrationData &data) {
    uint32_t flash_address = 0x080E0000;

    uint32_t register1[4] = {0};
    uint32_t register2[4] = {0};

    register1[3] = ((uint32_t)data.mag_radius << 16) | ((uint32_t)data.acc_radius);
    register1[2] = ((uint32_t)data.gyr_offset_x << 16) | ((uint32_t)data.gyr_offset_y);
    register1[1] = ((uint32_t)data.gyr_offset_z << 16) | ((uint32_t)data.mag_offset_x);
    register1[0] = ((uint32_t)data.mag_offset_y << 16) | ((uint32_t)data.mag_offset_z);

    register2[3] = ((uint32_t)data.acc_offset_x << 16) | ((uint32_t)data.acc_offset_y);
    register2[2] = ((uint32_t)data.acc_offset_z << 16) | ((uint32_t)data.calibration_status << 8);
    register2[1] = 0;
    register2[0] = 0;

    HAL_FLASH_Unlock();

    FLASH_EraseInitTypeDef EraseInitStruct;
    uint32_t SectorError;

    EraseInitStruct.TypeErase = FLASH_TYPEERASE_SECTORS;
    EraseInitStruct.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    EraseInitStruct.Sector = FLASH_SECTOR_11;
    EraseInitStruct.NbSectors = 1;

    if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
        HAL_FLASH_Lock();
        return;
    }

    for (int i = 0; i < 4; i++) {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, flash_address + (i * 4), register1[i]) != HAL_OK) {
            HAL_FLASH_Lock();
            return;
        }
    }

    for (int i = 0; i < 4; i++) {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, flash_address + 16 + (i * 4), register2[i]) != HAL_OK) {
            HAL_FLASH_Lock();
            return;
        }
    }

    HAL_FLASH_Lock();
}

bool BNO055::loadCalibration(CalibrationData &data) {
    uint32_t flash_address = 0x080E0000;

    uint32_t register1[4];
    uint32_t register2[4];

    for (int i = 0; i < 4; i++) {
        register1[i] = *(__IO uint32_t*)(flash_address + (i * 4));
    }

    for (int i = 0; i < 4; i++) {
        register2[i] = *(__IO uint32_t*)(flash_address + 16 + (i * 4));
    }

    data.mag_radius = (uint16_t)((register1[3] >> 16) & 0xFFFF);
    data.acc_radius = (uint16_t)(register1[3] & 0xFFFF);
    data.gyr_offset_x = (uint16_t)((register1[2] >> 16) & 0xFFFF);
    data.gyr_offset_y = (uint16_t)(register1[2] & 0xFFFF);
    data.gyr_offset_z = (uint16_t)((register1[1] >> 16) & 0xFFFF);
    data.mag_offset_x = (uint16_t)(register1[1] & 0xFFFF);
    data.mag_offset_y = (uint16_t)((register1[0] >> 16) & 0xFFFF);
    data.mag_offset_z = (uint16_t)(register1[0] & 0xFFFF);

    data.acc_offset_x = (uint16_t)((register2[3] >> 16) & 0xFFFF);
    data.acc_offset_y = (uint16_t)(register2[3] & 0xFFFF);
    data.acc_offset_z = (uint16_t)((register2[2] >> 16) & 0xFFFF);
    data.calibration_status = (uint8_t)((register2[2] >> 8) & 0xFF);

    return (data.calibration_status == 0x01);
}