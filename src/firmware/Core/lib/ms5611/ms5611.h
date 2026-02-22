#pragma once
#include <stdint.h>

class MS5611
{
public:

  bool begin() ;
  void calibrateSurface () ;
  float getTemperature() ;
  float getPressure() ;
  float getDepth() ;
private:

  uint16_t C1 ,C2 , C3 , C4 , C5 , C6 ;
  float surfacePressure ;
  float density = 1024.0 ;
  void readCalibrationData() ;
  void reset() ;
  uint32_t readADC() ;
};

//https://makerselectronics.com/wp-content/uploads/2025/09/ENG_DS_MS5611-01BA03_B3.pdf