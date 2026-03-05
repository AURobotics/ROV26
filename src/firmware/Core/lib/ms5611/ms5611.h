#pragma once
#include "stm32f4xx_hal.h"

#define i2cAddr (0x77 << 1)
class MS5611 {
public:
    explicit MS5611(I2C_HandleTypeDef* hi2c);
    MS5611() = default;
    bool begin();
    void calibrateSurface();
    float getTemperature();
    float getPressure();
    float getDepth();

private:
    I2C_HandleTypeDef* _hi2c{};
    uint16_t C1{}, C2{}, C3{}, C4{}, C5{}, C6{};
    float surfacePressure{};
    float density = 1024.0;
    void readCalibrationData();
    void reset();
    void sendCmd(uint8_t cmd);
    uint32_t readADC();
    static uint16_t readPROM(I2C_HandleTypeDef* hi2c, uint8_t addr);
};

// https://makerselectronics.com/wp-content/uploads/2025/09/ENG_DS_MS5611-01BA03_B3.pdf
