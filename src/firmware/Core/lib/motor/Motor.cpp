#include "Motor.h"
#include <cmath>

float constrain(const float x, const float a, const float b) { return x > b ? b : x < a ? a : x; }

Motor::Motor(const PWM& p1, const PWM& p2) : pwm1(p1), pwm2(p2) {}

void Motor::setup() const {
    pwm1.start();
    pwm2.start();
}

void Motor::move(float speed) const {
    speed = constrain(speed, -1, 1);

    const auto duty = static_cast<uint16_t>(std::fabs(speed) * 255);

    if (speed > 0) {
        pwm1.set_duty(duty);
        pwm2.set_duty(0);
    }
    else if (speed < 0) {
        pwm1.set_duty(0);
        pwm2.set_duty(duty);
    }
}

void Motor::stop() const {
    pwm1.set_duty(255);
    pwm2.set_duty(255);
}
