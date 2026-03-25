#include "Motor.h"
#include <cmath>
#include "stm32f4xx_hal.h"


float constrain(const float x, const float a, const float b) { return x > b ? b : x < a ? a : x; }


// Motor::Motor(PWM& p1, PWM& p2) : pwm1(p1), pwm2(p2) {}
// Motor::Motor(std::function<void(float)> customHandler) : handler(std::move(customHandler)) {}

void Motor::setup() const {
    switch (this->handler_type) {
    case HandlerType::FUNCTION :
        return;
    case HandlerType::PWM :
        HAL_TIM_PWM_Start(pwm_1.htim, pwm_1.channel);
        HAL_TIM_PWM_Start(pwm_2.htim, pwm_2.channel);
    }
}

void Motor::move(float speed) const {
    speed = constrain(speed, -1, 1);
    switch (this->handler_type) {
    case HandlerType::FUNCTION :
        handler_function(speed);
        return;
    case HandlerType::PWM :;
        speed = constrain(speed, -1, 1);
        const auto duty = static_cast<uint16_t>(std::fabs(speed) * 999);
        if (speed > 0) {
            __HAL_TIM_SET_COMPARE(pwm_1.htim, pwm_1.channel, duty);
            __HAL_TIM_SET_COMPARE(pwm_2.htim, pwm_2.channel, 0);
        }
        else if (speed <= 0) {
            __HAL_TIM_SET_COMPARE(pwm_1.htim, pwm_1.channel, 0);
            __HAL_TIM_SET_COMPARE(pwm_2.htim, pwm_2.channel, duty);
        }
    }
}


void Motor::stop() const { move(0); }

void Motor::move_motor(Motor motors[8], float speeds[8]) {
    for (int i = 0; i < 8; i++)
        motors[i].move(speeds[i]);
}
