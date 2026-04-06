#ifndef BMP_H
#define BMP_H

#include <Wire.h>
#include <stdint.h>

#define BMP_ADDR  0x76

class BMP {
public:
    BMP(uint8_t addr = BMP_ADDR);

    bool  begin();
    void  calibrateSurface();
    float getTemperature();   // °C
    float getPressure();      // Pa
    float getDepth();         

private:
    uint8_t _addr;
    float   surfacePressure;
    float   density = 1000.0f;  
    uint16_t dig_T1;
    int16_t  dig_T2, dig_T3;
    uint16_t dig_P1;
    int16_t  dig_P2, dig_P3, dig_P4, dig_P5;
    int16_t  dig_P6, dig_P7, dig_P8, dig_P9;

    int32_t  t_fine;

    void     reset();
    void     readTrimData();
   
    void     writeReg(uint8_t reg, uint8_t value);
    uint8_t  readReg(uint8_t reg);
    void     readRegs(uint8_t reg, uint8_t *buf, uint8_t len);

    int32_t  compensateTemp(int32_t adc_T);
    uint32_t compensatePressure(int32_t adc_P);
};

#endif 