#pragma once
#include "stm32f4xx_hal.h"

class PWM {
    TIM_HandleTypeDef* htim;
    uint32_t channel;

public:
    PWM(TIM_HandleTypeDef* timer, uint32_t ch);
    void start() const;
    void set_duty(uint16_t duty) const; // 0–255
};
