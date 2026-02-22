#include "ms5611.h"
// #include "i2c.h"

#define RESET    0x1E
#define D1_P  0x48 // raw pressure
#define D2_T  0x58 // raw temperature
#define ADC_READ 0x00
#define PROM_READ 0xA0

extern void delay_ms(uint32_t ms);


MS5611::MS5611(I2C *i2c) {
    i2c_bus = i2c;
}

bool MS5611::begin() {
    reset();
    delay_ms(10);
    readCalibrationData();
    calibrateSurface();
    return true;
}

void MS5611::reset() {
    i2c_bus->write_reg(RESET, 0x00);
}

void MS5611::readCalibrationData() {
    i2c_bus->read_2reg(0xA2, 0xA3, &C1);
    i2c_bus->read_2reg(0xA4, 0xA5, &C2);
    i2c_bus->read_2reg(0xA6, 0xA7, &C3);
    i2c_bus->read_2reg(0xA8, 0xA9, &C4);
    i2c_bus->read_2reg(0xAA, 0xAB, &C5);
    i2c_bus->read_2reg(0xAC, 0xAD, &C6);
}

uint32_t MS5611::readADC() {
    uint8_t b1, b2, b3;

    i2c_bus->read_reg(ADC_READ, &b1);
    i2c_bus->read_reg(ADC_READ, &b2);
    i2c_bus->read_reg(ADC_READ, &b3);

    return ((uint32_t)b1 << 16) | ((uint32_t)b2 << 8) | b3;
}

float MS5611::getTemperature() {
    i2c_bus->write_reg(D2_T, 0);
    delay_ms(10);

    uint32_t D2 = readADC();
    int32_t dT = D2 - ((int32_t)C5 << 8);
    int32_t TEMP = 2000 + ((int64_t)dT * C6 >> 23);

    return TEMP / 100.0f;
}

float MS5611::getPressure() {
    i2c_bus->write_reg(D1_P, 0);
    delay_ms(10);
    uint32_t D1 = readADC();  // raw pressure

    i2c_bus->write_reg(D2_T, 0);
    delay_ms(10);
    uint32_t D2 = readADC(); // raw temperature

    int32_t dT = D2 - ((int32_t)C5 << 8);

    int64_t OFFSET  = ((int64_t)C2 << 16) + ((int64_t)C4 * dT >> 7);
    int64_t SENSITIVITY = ((int64_t)C1 << 15) + ((int64_t)C3 * dT >> 8);

    int32_t P = (((D1 * SENSITIVITY) >> 21) - OFFSET) >> 15;

    return P * 100.0f; // Pa
}

void MS5611::calibrateSurface() {
  constexpr int samples = 5;
    float sum = 0.0f;

    for (int i = 0; i < samples; i++) {
        sum += getPressure();
        delay_ms(20);
    }

    surfacePressure = sum / samples;
}

float MS5611::getDepth() {
  const float p = getPressure();
    return (p - surfacePressure) / (density * 9.80665f);
}