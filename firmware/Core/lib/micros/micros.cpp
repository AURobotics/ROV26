#include "micros.h"
#include "stm32f4xx_hal.h"

static volatile uint32_t ms_count = 0;

void TIM11_Init(void)
{
    __HAL_RCC_TIM11_CLK_ENABLE();
    TIM11->PSC  = 83; // prescaler
    TIM11->ARR  = 999; // 1000 tick(top)
    TIM11->CNT  = 0; // timer starts at 0
    TIM11->DIER |= TIM_DIER_UIE;//enable timer interrupt
    TIM11->SR   &= ~TIM_SR_UIF;//reset flag
    HAL_NVIC_EnableIRQ(TIM1_TRG_COM_TIM11_IRQn); //enable ISR
    TIM11->CR1  |= TIM_CR1_CEN;//start the timer
}

extern "C" void TIM1_TRG_COM_TIM11_IRQHandler(void)
{
    if (TIM11->SR & TIM_SR_UIF)
    {
        TIM11->SR &= ~TIM_SR_UIF;// reset interrupt flag
        ms_count++;
    }
}

uint32_t micros(void)
{
    uint32_t ms;
    uint32_t cnt;

    do {
        ms  = ms_count;
        cnt = TIM11->CNT;
    } while (ms != ms_count);

    return ms * 1000 + cnt;
}