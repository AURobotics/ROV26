#pragma once
#include "pwm.h"

class Motor {
    const PWM &pwm1, &pwm2;

public:
    Motor(const PWM& p1,  const PWM& p2);
    void setup() const;
    void move(float speed) const;
    void stop() const;
    static void move_motor(Motor motors[8], float speeds[8]);
};
