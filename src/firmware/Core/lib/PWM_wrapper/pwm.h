#pragma once
#include "stm32f4xx_hal.h"


class PWM {
private:
    TIM_HandleTypeDef* htim;
    uint32_t channel;

public:
    PWM(TIM_HandleTypeDef* timer, uint32_t ch);

    void start();
    void setDuty(uint16_t duty); // 0–255
};
