#include "bmp280.h"

#define CALIB00   0x88   
#define ID        0xD0   
#define RESET     0xE0
// #define STATUS    0xF3 //FORCED MODE only
#define CTRL_MEAS 0xF4
#define CONFIG_VAL  0x10 
#define PRESS_MSB 0xF7  

#define CTRL_NORMAL   0x77 
#define REG_CONFIG    0xF5  
#define RESET_VAL     0xB6

BMP::BMP(uint8_t addr) {
    _addr = addr;
}

void BMP::writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(_addr);
    Wire.write(reg);
    Wire.write(value);
    Wire.endTransmission();
}

uint8_t BMP::readReg(uint8_t reg) {
    Wire.beginTransmission(_addr);
    Wire.write(reg);
    Wire.endTransmission();
    Wire.requestFrom(_addr, (uint8_t)1);
    return Wire.read();
}

void BMP::readRegs(uint8_t reg, uint8_t *buf, uint8_t len) {
    Wire.beginTransmission(_addr);
    Wire.write(reg);
    Wire.endTransmission();
    Wire.requestFrom(_addr, len);
    for (uint8_t i = 0; i < len; i++) {
        buf[i] = Wire.read();
    }
}



void BMP::reset() {
    writeReg(RESET, RESET_VAL);
    delay(3);  
}

void BMP::readTrimData() {
    uint8_t buf[24];
    readRegs(CALIB00, buf, 24);

    // Temperature trim
    dig_T1 = (uint16_t)(buf[1] << 8) | buf[0];
    dig_T2 = (int16_t) (buf[3] << 8) | buf[2];
    dig_T3 = (int16_t) (buf[5] << 8) | buf[4];

    // Pressure trim
    dig_P1 = (uint16_t)(buf[7]  << 8) | buf[6];
    dig_P2 = (int16_t) (buf[9]  << 8) | buf[8];
    dig_P3 = (int16_t) (buf[11] << 8) | buf[10];
    dig_P4 = (int16_t) (buf[13] << 8) | buf[12];
    dig_P5 = (int16_t) (buf[15] << 8) | buf[14];
    dig_P6 = (int16_t) (buf[17] << 8) | buf[16];
    dig_P7 = (int16_t) (buf[19] << 8) | buf[18];
    dig_P8 = (int16_t) (buf[21] << 8) | buf[20];
    dig_P9 = (int16_t) (buf[23] << 8) | buf[22];
}

bool BMP::begin() {
    reset();
    readTrimData();
    writeReg(CTRL_MEAS, CTRL_NORMAL);  
    writeReg(REG_CONFIG, CONFIG_VAL);
    calibrateSurface();
    return true;
}

int32_t BMP::compensateTemp(int32_t adc_T) {
    int32_t var1, var2, T;

    var1 = ((((adc_T >> 3) - ((int32_t)dig_T1 << 1)))  //--> (adc_T / 8 - dig_T1 * 2)
             * ((int32_t)dig_T2)) >> 11;

    var2 = (((((adc_T >> 4) - ((int32_t)dig_T1))
              * ((adc_T >> 4) - ((int32_t)dig_T1))) >> 12)
             * ((int32_t)dig_T3)) >> 14;   //--> ((adc_T / 16 - dig_T1)² / 4096) * dig_T3 / 16384

    t_fine = var1 + var2;
    T = (t_fine * 5 + 128) >> 8;   // T is in °C × 100
    return T;
}


uint32_t BMP::compensatePressure(int32_t adc_P) {
    int64_t var1, var2, p;

    var1 = ((int64_t)t_fine) - 128000;
    var2 = var1 * var1 * (int64_t)dig_P6;
    var2 = var2 + ((var1 * (int64_t)dig_P5) << 17);
    var2 = var2 + (((int64_t)dig_P4) << 35);
    var1 = ((var1 * var1 * (int64_t)dig_P3) >> 8)
           + ((var1 * (int64_t)dig_P2) << 12);
    var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)dig_P1) >> 33;

    if (var1 == 0) return 0;   // avoid division by zero

    p    = 1048576 - adc_P;
    p    = (((p << 31) - var2) * 3125) / var1;
    var1 = (((int64_t)dig_P9) * (p >> 13) * (p >> 13)) >> 25;
    var2 = (((int64_t)dig_P8) * p) >> 19;
    p    = ((p + var1 + var2) >> 8) + (((int64_t)dig_P7) << 4);

    return (uint32_t)p;   
}


float BMP::getTemperature() {
    
    uint8_t buf[3];
    readRegs(PRESS_MSB + 3, buf, 3);   

    int32_t adc_T = ((int32_t)buf[0] << 12)
                  | ((int32_t)buf[1] <<  4)
                  | ((int32_t)buf[2] >>  4);

    int32_t T = compensateTemp(adc_T);
    return T / 100.0f;   // °C
}

float BMP::getPressure() {
 
   
    uint8_t buf[6];
    readRegs(PRESS_MSB, buf, 6);

    int32_t adc_P = ((int32_t)buf[0] << 12)
                  | ((int32_t)buf[1] <<  4)
                  | ((int32_t)buf[2] >>  4);

    int32_t adc_T = ((int32_t)buf[3] << 12)
                  | ((int32_t)buf[4] <<  4)
                  | ((int32_t)buf[5] >>  4);


    compensateTemp(adc_T);

    uint32_t P = compensatePressure(adc_P);
    return (float)(P >> 8)          
         + ((P & 0xFF) / 256.0f);    
}

void BMP::calibrateSurface() {
    const int samples = 5;
    float sum = 0.0f;

    for (int i = 0; i < samples; i++) {
        sum += getPressure();
        delay(20);
    }

    surfacePressure = sum / samples;
}

float BMP::getDepth() {
    float p = getPressure();
    return (p - surfacePressure) / (density * 9.80665f);
}