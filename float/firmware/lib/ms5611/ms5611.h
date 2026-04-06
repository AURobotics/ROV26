#ifndef MS5611_H
#define MS5611_H

#include <Wire.h>
#include <stdint.h>

#define MS5611_ADDR  0x77   

class MS5611 {
public:
    MS5611(uint8_t addr = MS5611_ADDR);

    bool  begin();
    void  calibrateSurface();
    float getTemperature();
    float getPressure();
    float getDepth();

private:
    uint8_t  _addr;
    uint16_t C1, C2, C3, C4, C5, C6;
    float    surfacePressure;
    float    density = 1025f;   

    void     reset();
    void     sendCmd(uint8_t cmd);
    uint32_t readADC();
    uint16_t readPROM(uint8_t prom_addr);
    void     readCalibrationData();
};

#endif
