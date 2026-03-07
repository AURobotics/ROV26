#include "ms5611.h"

#define RESET 0x1E
#define D1_P 0x48 // raw pressure
#define D2_T 0x58 // raw temperature
#define ADC_READ 0x00
#define PROM_READ 0xA0

MS5611::MS5611(I2C_HandleTypeDef* hi2c) : _hi2c(hi2c) {}

void MS5611::sendCmd(uint8_t cmd) {
    HAL_I2C_Master_Transmit(_hi2c, i2cAddr, &cmd, 1, HAL_MAX_DELAY);
}

bool MS5611::begin() {
    reset();

    readCalibrationData();
    calibrateSurface();
    return true;
}

void MS5611::reset() {
    sendCmd(RESET);
    HAL_Delay(3);
}
uint16_t MS5611::readPROM(I2C_HandleTypeDef* hi2c, uint8_t addr) {
    uint8_t data[2];
    HAL_I2C_Master_Transmit(hi2c, i2cAddr, &addr, 1, HAL_MAX_DELAY);
    HAL_I2C_Master_Receive(hi2c, i2cAddr, data, 2, HAL_MAX_DELAY);
    return (data[0] << 8) | data[1];
}
void MS5611::readCalibrationData() {
    C1 = readPROM(_hi2c, 0XA2);
    C2 = readPROM(_hi2c, 0XA4);
    C3 = readPROM(_hi2c, 0XA6);
    C4 = readPROM(_hi2c, 0XA8);
    C5 = readPROM(_hi2c, 0XAA);
    C6 = readPROM(_hi2c, 0XAC);
}

uint32_t MS5611::readADC() {
    uint8_t buffer[3];
    uint8_t cmd = ADC_READ;

    HAL_I2C_Master_Transmit(_hi2c, i2cAddr, &cmd, 1, HAL_MAX_DELAY);
    HAL_I2C_Master_Receive(_hi2c, i2cAddr, buffer, 3, HAL_MAX_DELAY);

    return ((uint32_t)buffer[0] << 16) | ((uint32_t)buffer[1] << 8) | buffer[2];
}

float MS5611::getTemperature() {
    sendCmd(D2_T);
    HAL_Delay(10);

    uint32_t D2 = readADC();
    int32_t dT = D2 - ((int32_t)C5 << 8);
    int32_t temp = 2000 + ((int64_t)dT * C6 >> 23);

    return temp / 100.0f; // °C
}

float MS5611::getPressure() {
    sendCmd(D1_P);
    HAL_Delay(10);
    uint32_t D1 = readADC(); // raw pressure

    sendCmd(D2_T);
    HAL_Delay(10);
    uint32_t D2 = readADC(); // raw temperature

    int32_t dT = D2 - ((int32_t)C5 << 8);

    int64_t OFFSET = ((int64_t)C2 << 16) + ((int64_t)C4 * dT >> 7);
    int64_t SENSITIVITY = ((int64_t)C1 << 15) + ((int64_t)C3 * dT >> 8);

    int32_t P = (((((int64_t)D1 * SENSITIVITY) >> 21) - OFFSET) >> 15);

    return P * 100.0f; // Pa
}

void MS5611::calibrateSurface() {
    const int samples = 5;
    float sum = 0.0f;

    for (int i = 0; i < samples; i++) {
        sum += getPressure();
        HAL_Delay(20);
    }

    surfacePressure = sum / samples;
}

float MS5611::getDepth() {
    float p = getPressure();
    return (p - surfacePressure) / (density * 9.80665f);
}
