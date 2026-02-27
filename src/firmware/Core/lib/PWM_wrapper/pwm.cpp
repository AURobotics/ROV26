#include "pwm.h"

PWM::PWM(TIM_HandleTypeDef* timer, uint32_t ch) {
    htim = timer;
    channel = ch;
}

void PWM::start() const { HAL_TIM_PWM_Start(htim, channel); }

void PWM::set_duty(uint16_t duty) const { __HAL_TIM_SET_COMPARE(htim, channel, duty); }
