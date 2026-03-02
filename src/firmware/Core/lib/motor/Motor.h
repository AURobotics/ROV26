#pragma once
#include <functional>
#include "pwm.h"

class Motor {
    PWM &pwm1, &pwm2;
    std::function<void(float)> handler{};

public:
    Motor(const PWM& p1, const PWM& p2);
    explicit Motor(std::function<void(float)> Handler);
    void setup() const;
    void move(float speed) const;
    void stop() const;
    static void move_motor(Motor motors[8], float speeds[8]);
};
