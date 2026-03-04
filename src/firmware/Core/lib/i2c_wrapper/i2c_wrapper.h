#pragma once

// #include "stm32f4xx_hal.h"
extern "C" {
#include "i2c.h"
}

class I2C {
    I2C_HandleTypeDef* i2cHandle;

public:
    explicit I2C(I2C_HandleTypeDef* i2c_Handle);

    HAL_StatusTypeDef read_reg(uint8_t sensor_addr, uint8_t reg_addr, uint8_t* reg_data,
                               uint8_t len = 1) const;
    HAL_StatusTypeDef write_reg(uint8_t sensor_addr, uint8_t reg_addr, uint8_t data) const;
    bool read_2reg(uint8_t sensor_addr, uint8_t reg_addr_msb, uint8_t reg_addr_lsb,
                   uint16_t* reg_data) const;
    void write_2reg(uint8_t sensor_addr, uint8_t reg_addr_msb, uint8_t reg_addr_lsb,
                    uint16_t reg_data) const;
};
