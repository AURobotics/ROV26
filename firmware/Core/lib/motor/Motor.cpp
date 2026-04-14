#include "Motor.h"

#include <algorithm>
#include <cfloat>
#include <cmath>

#include "main.h"
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

int Motor::move(float speed) {
    if (std::abs(speed) <= FLT_EPSILON) {
        __HAL_TIM_SET_COMPARE(pwm_1.htim, pwm_1.channel, 0);
        __HAL_TIM_SET_COMPARE(pwm_2.htim, pwm_2.channel, 0);
        return 0;
    }

    speed = std::clamp(speed, -1.0f, 1.0f);
    float abs_speed = std::fabs(speed);
    float mapped_speed = m_starting_speed + abs_speed * (1.0f - m_starting_speed);
    const auto duty = static_cast<uint16_t>(mapped_speed * 1000.0f);

    if (speed > 0) {
        __HAL_TIM_SET_COMPARE(pwm_1.htim, pwm_1.channel, duty);
        __HAL_TIM_SET_COMPARE(pwm_2.htim, pwm_2.channel, 0);

    }
    else if (speed < 0) {
        __HAL_TIM_SET_COMPARE(pwm_2.htim, pwm_2.channel, duty);
        __HAL_TIM_SET_COMPARE(pwm_1.htim, pwm_1.channel, 0);
    }
    this->val = std::signbit(speed) ? -duty : duty;
    return this->val;
}

int Motor::stop() {return move(0.0f); }

void Motor::swap_direction() { std::swap(pwm_1, pwm_2); }

void Motor::move_array(Motor motors[8], float speeds[8]) {
    for (int i = 0; i < 8; i++)
        motors[i].move(speeds[i]);
}
