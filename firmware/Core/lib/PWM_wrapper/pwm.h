#pragma once
#include "stm32f4xx_hal.h"

class PWM {
    TIM_HandleTypeDef* htim;
    uint32_t channel;

public:
    explicit constexpr PWM(TIM_HandleTypeDef* timer, uint32_t ch) : htim(timer), channel(ch) {}
    PWM(const PWM&) = delete; // copy constructor
    PWM& operator=(const PWM&) = delete;

    PWM(PWM&&) = default; // move constructor
    PWM& operator=(PWM&&) = default;
    void start() const;
    void set_duty(uint16_t duty) const; // 0–255
};
