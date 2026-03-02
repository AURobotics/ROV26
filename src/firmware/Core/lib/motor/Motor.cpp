#include "Motor.h"
#include <cmath>

float constrain(const float x, const float a, const float b) { return x > b ? b : x < a ? a : x; }

Motor::Motor(const PWM& p1, const PWM& p2) : pwm1(p1), pwm2(p2) {}
Motor::Motor(std::function<void(float)> customHandler) : pwm1(), pwm2(), handler(customHandler) {}

void Motor::setup() const {
    if (handler)
        return;
    pwm1.start();
    pwm2.start();
}

void Motor::move(float speed) const {
    if (handler) {
        handler(speed);
        return;
    }

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
    if (handler) {
        handler(0);
        return;
    }
    pwm1.set_duty(255);
    pwm2.set_duty(255);
}

void Motor::move_motor(Motor motors[8], float speeds[8]) {
    for (int i = 0; i < 8; i++)
        motors[i].move(speeds[i]);
}
