#pragma once

#include "pwm.h"


class Motor {
    enum class HandlerType : uint8_t { FUNCTION, PWM } handler_type;

    struct pwm {
        TIM_HandleTypeDef* htim;
        uint8_t channel;
    } pwm_1{}, pwm_2{};

    void (*handler_function)(float){};


public:
    explicit constexpr Motor(void (*fn)(float)) : handler_type(HandlerType::FUNCTION) {
        handler_function = fn;
    }

    explicit constexpr Motor(const pwm p1, const pwm p2) :
        handler_type(HandlerType::PWM), pwm_1(p1), pwm_2(p2) {}
    Motor(const Motor&) = delete;
    Motor& operator=(const Motor&) = delete;
    void setup() const;
    void move(float speed) const;
    void stop() const;
    static void move_motor(Motor motors[8], float speeds[8]);
};
