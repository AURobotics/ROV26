#include "i2c_wrapper.h"


I2C::I2C(I2C_HandleTypeDef* i2c_Handle) {
    i2cHandle = i2c_Handle;
}

HAL_StatusTypeDef I2C::read_reg(const uint8_t sensor_addr, const uint8_t reg_addr,
                                uint8_t* reg_data, const uint8_t len) const {
    return HAL_I2C_Mem_Read(i2cHandle,
                            (sensor_addr << 1),
                            reg_addr,
                            I2C_MEMADD_SIZE_8BIT,
                            reg_data,
                            len,
                            HAL_MAX_DELAY);
}
HAL_StatusTypeDef I2C::write_reg(const uint8_t sensor_addr, const uint8_t reg_addr,
                                 uint8_t data) const {
    return HAL_I2C_Mem_Write(
        i2cHandle, (sensor_addr << 1), reg_addr, I2C_MEMADD_SIZE_8BIT, &data, 1, HAL_MAX_DELAY);
}
bool I2C::read_2reg(const uint8_t sensor_addr, const uint8_t reg_addr_msb, uint8_t reg_addr_lsb,
                    uint16_t* reg_data) const {
    uint8_t msb, lsb;
    if (read_reg(sensor_addr, reg_addr_lsb, &lsb) && read_reg(sensor_addr, reg_addr_msb, &msb)) {
        *reg_data = msb << 8 | lsb;
        return true;
    }
    return false;
}

void I2C::write_2reg(uint8_t sensor_addr, uint8_t reg_addr_msb, uint8_t reg_addr_lsb,
                      uint16_t reg_data) const {
    uint8_t msb = (reg_data >> 8) & 0b11111111;
    uint8_t lsb = reg_data & 0b11111111;
    // ReSharper disable once CppExpressionWithoutSideEffects
    write_reg(sensor_addr, reg_addr_lsb, lsb);
    // ReSharper disable once CppExpressionWithoutSideEffects
    write_reg(sensor_addr, reg_addr_msb, msb);
}
