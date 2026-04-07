#include "ms5611.h"

#define RESET    0x1E
#define D1_P     0x48   // raw pressure  
#define D2_T     0x58   // raw temperature
#define ADC_READ 0x00
#define PROM_READ 0xA0

// ============================================================

MS5611::MS5611(uint8_t addr) {
    _addr = addr;
}

void MS5611::sendCmd(uint8_t cmd) {
    Wire.beginTransmission(_addr);
    Wire.write(cmd);
    Wire.endTransmission();
}

uint16_t MS5611::readPROM(uint8_t prom_addr) {
    Wire.beginTransmission(_addr);
    Wire.write(prom_addr);
    Wire.endTransmission();

    Wire.requestFrom(_addr, (uint8_t)2);
    uint8_t hi = Wire.read(); 
    uint8_t lo = Wire.read();
    return (uint16_t)(hi << 8) | lo;
}

uint32_t MS5611::readADC() {
    Wire.beginTransmission(_addr);
    Wire.write(ADC_READ);
    Wire.endTransmission();

    Wire.requestFrom(_addr, (uint8_t)3);
    uint8_t b0 = Wire.read();
    uint8_t b1 = Wire.read();
    uint8_t b2 = Wire.read();
    return ((uint32_t)b0 << 16) | ((uint32_t)b1 << 8) | b2;
}


void MS5611::reset() {
    sendCmd(RESET);
    delay(3);
}

void MS5611::readCalibrationData() {
    C1 = readPROM(0xA2);
    C2 = readPROM(0xA4);
    C3 = readPROM(0xA6);
    C4 = readPROM(0xA8);
    C5 = readPROM(0xAA);
    C6 = readPROM(0xAC);
}

bool MS5611::begin() {
    reset();
    readCalibrationData();
    calibrateSurface();
    return true;
}

float MS5611::getTemperature() {
    sendCmd(D2_T);
    delay(10);

    uint32_t D2  = readADC();
    int32_t  dT  = (int32_t)D2 - ((int32_t)C5 << 8);
    int32_t  temp = 2000 + (int32_t)(((int64_t)dT * C6) >> 23);

    return temp / 100.0f;   // °C
}

float MS5611::getPressure() {
    sendCmd(D1_P);
    delay(10);
    uint32_t D1 = readADC();    // raw pressure

    sendCmd(D2_T);
    delay(10);
    uint32_t D2 = readADC();    // raw temperature

    int32_t  dT          = (int32_t)D2 - ((int32_t)C5 << 8);
    int64_t  OFFSET      = ((int64_t)C2 << 16) + (((int64_t)C4 * dT) >> 7);
    int64_t  SENSITIVITY = ((int64_t)C1 << 15) + (((int64_t)C3 * dT) >> 8);

    int32_t  P = (int32_t)((((int64_t)D1 * SENSITIVITY >> 21) - OFFSET) >> 15);

    return (float)P;   // Pa
}
void MS5611::calibrateSurface() {
    const int samples = 5;
    float sum = 0.0f;

    for (int i = 0; i < samples; i++) {
        sum += getPressure();
        delay(20);
    }

    surfacePressure = sum / samples;
}
float MS5611::getDepth() {
    float p = getPressure();
    return (p - surfacePressure) / (density * 9.80665f);
}
