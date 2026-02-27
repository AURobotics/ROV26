#include "pwm.h"

PWM::PWM(TIM_HandleTypeDef* timer, uint32_t ch) {
    htim = timer;
    channel = ch;
}

void PWM::start() { HAL_TIM_PWM_Start(htim, channel); }

void PWM::setDuty(uint16_t duty) { __HAL_TIM_SET_COMPARE(htim, channel, duty); }
