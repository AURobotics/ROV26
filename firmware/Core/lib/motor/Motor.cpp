#include "Motor.h"
#include <cmath>
#include <utility>

float constrain(const float x, const float a, const float b) { return x > b ? b : x < a ? a : x; }


// Motor::Motor(PWM& p1, PWM& p2) : pwm1(p1), pwm2(p2) {}
// Motor::Motor(std::function<void(float)> customHandler) : handler(std::move(customHandler)) {}

void Motor::setup() const {
    switch (this->handler_type) {
    case HandlerType::FUNCTION :
        return;
    case HandlerType::PWM :
        Handler.pwm_handler.p1->start();
        Handler.pwm_handler.p2->start();
        break;
    }
}

void Motor::move(float speed) const {
    speed = constrain(speed, -1, 1);
    switch (this->handler_type) {
    case HandlerType::FUNCTION :
        Handler.handler_function(speed);
        return;
    case HandlerType::PWM :
        const auto pwm1 = this->Handler.pwm_handler.p1;
        const auto pwm2 = this->Handler.pwm_handler.p2;
        speed = constrain(speed, -1, 1);
        const auto duty = static_cast<uint16_t>(std::fabs(speed) * 255);
        if (speed > 0) {
            pwm1->set_duty(duty);
            pwm2->set_duty(0);
        }
        else if (speed <= 0) {
            pwm1->set_duty(0);
            pwm2->set_duty(duty);
        }
    }
}


void Motor::stop() const {
    switch (this->handler_type) {
    case HandlerType::FUNCTION :
        move(0);
        return;
    case HandlerType::PWM :
        const auto pwm1 = this->Handler.pwm_handler.p1;
        const auto pwm2 = this->Handler.pwm_handler.p2;
        pwm1->set_duty(255);
        pwm2->set_duty(255);
    }
}

void Motor::move_motor(Motor motors[8], float speeds[8]) {
    for (int i = 0; i < 8; i++)
        motors[i].move(speeds[i]);
}
