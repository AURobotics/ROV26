#include "main.h"
#include "Controller.h"
#include "Motor.h"
#include "PID.h"
#include "adc.h"
#include "bno055.h"
#include "gpio.h"
#include "i2c.h"
#include "i2c_wrapper.h"
#include "ms5611.h"
#include "tim.h"
#include "usb_comms.h"
#include "usb_device.h"
#include "usbd_cdc.h"

#include <cstdio>
#include <optional>

#include "Kinematics.h"
#include "array"
#include "usbd_cdc_if.h"

I2C i2c_wrapper(&hi2c3); 
BNO055 bno(&i2c_wrapper)
MS5611 ms5611(&hi2c3);

// yaw, angular yaw, pitch, angular pitch, roll, angular roll, depth, nullopt
std::array<std::optional<float>, 8> fetch_sensor_data(bool use_angle_rates) {
    std::array<std::optional<float>, 8> data;

    data[0].value() = ms5611.getDepth();
    data[1] = std::nullopt;
    data[2] = bno.euler_angles().x;
    data[3] = bno.get_body_rates().roll;
    data[4] = bno.euler_angles().y;
    data[5] = bno.get_body_rates().pitch;
    data[6] = bno.euler_angles().z;
    data[7] = bno.get_body_rates().yaw;

    return data;
}

TxPacket dummy = {
    .sync_byte    = 0xFF,
    .motor_speeds = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f},
    .gripper_speed = 0.5f,
    .depth        = 10.5f,
    .yaw          = 45.0f,
    .pitch        = -15.0f,
    .roll         = 5.0f,
    .status_byte  = 0x01
};

void SystemClock_Config(void);

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void) {

    HAL_Init();
    SystemClock_Config();

    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_I2C3_Init();
    MX_TIM1_Init();
    MX_TIM2_Init();
    MX_TIM3_Init();
    MX_TIM4_Init();
    MX_TIM5_Init();
    MX_USB_DEVICE_Init();



    uint32_t last_send_time = 0;
    // depth roll pitch yaw
    unsigned char control_byte{};
    float data[6] = {}; // Fx Fy Fz Froll Fpitch Fyaw
    float setpoint[4]{};
    float controller_output[6] = {}; // depth pitch roll yaw surge sway

    float hold[4] = {}; // yaw pirch roll depth

    /*Initialize all controllers: depth roll pitch yaw*/
    Controller controller[4] = {Controller(PID(0, 0, 0)),
                                Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
                                Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
                                Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0)))};

    Motor motors[8] = {Motor(), Motor(), Motor(), Motor(), Motor(), Motor(), Motor(), Motor()};

    float prev{};
    float now = HAL_GetTick();

    std::array<std::optional<float>, 8> sensor_data;

    while (true) {
        RxPacket rx_pkt;
        TxPacket tx_pkt;
        switch (flow_state) {
        case FLOW_RECEIVING :
            if (data_received) {
                data_received = 0;
                memcpy(&rx_pkt, rx_buffer, sizeof(RxPacket));
                flow_state = FLOW_SENDING;
            }
            else {
                flow_state = FLOW_WAITING; // no data received, signal Pi
            }
            break;

        case FLOW_WAITING :
            CDC_Transmit_FS(&ready_byte, 1);
            flow_state = FLOW_RECEIVING;
            break;

        case FLOW_SENDING :
            if (HAL_GetTick() - last_send_time >= 40) {
                last_send_time = HAL_GetTick();
                load_tx(&tx_pkt);
                CDC_Transmit_FS((uint8_t*)&tx_pkt, sizeof(TxPacket));
                flow_state = FLOW_RECEIVING;
            }
            break;
        }
        sensor_data = fetch_sensor_data(true);

        prev = now;
        now = HAL_GetTick();
        float dt = (now - prev) / 1000.0; // convert ms->seconds


        for (int i = 0, j = 0; i < 8; i += 2, j++)
            if (control_byte & 1 << (7 - j)) // setpoint
                controller_output[j + 2] = controller[j].output(
                    setpoint[j], sensor_data[i].value(), dt, sensor_data[i + 1].value());
            else {
                if (data[j + 2] == 0) // hold position
                    controller_output[j + 2] = controller[j].output(
                        hold[j], sensor_data[i].value(), dt, sensor_data[i + 1].value());
                else { // pilot command
                    controller_output[j + 2] = data[j + 2];
                    hold[j] = sensor_data[i].value();
                }
            }

        // surge
        controller_output[0] = data[0];
        // sway
        controller_output[1] = data[1];
    }
    float clamped_motors[8] = {};
    apply_pseudo_inverse(controller_output, clamped_motors);
    Motor::move_motor(motors, clamped_motors);
}

/**
 * @brief System Clock Configuration
 * @retval None
 */
void SystemClock_Config(void) {
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /** Configure the main internal regulator output voltage
     */
    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE2);

    /** Initializes the RCC Oscillators according to the specified parameters
     * in the RCC_OscInitTypeDef structure.
     */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 25;
    RCC_OscInitStruct.PLL.PLLN = 384;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV6;
    RCC_OscInitStruct.PLL.PLLQ = 8;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        Error_Handler();
    }

    /** Initializes the CPU, AHB and APB buses clocks
     */
    RCC_ClkInitStruct.ClockType =
        RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK) {
        Error_Handler();
    }

    /** Enables the Clock Security System
     */
    HAL_RCC_EnableCSS();
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
 * @brief  This function is executed in case of error occurrence.
 * @retval None
 */
void Error_Handler(void) {
    /* USER CODE BEGIN Error_Handler_Debug */
    /* User can add his own implementation to report the HAL error return state
     */
    __disable_irq();
    while (1) {
    }
    /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
 * @brief  Reports the name of the source file and the source line number
 *         where the assert_param error has occurred.
 * @param  file: pointer to the source file name
 * @param  line: assert_param error line source number
 * @retval None
 */
void assert_failed(uint8_t* file, uint32_t line) {
    /* USER CODE BEGIN 6 */
    /* User can add his own implementation to report the file name and line
       number, ex: printf("Wrong parameters value: file %s on line %d\r\n",
       file, line) */
    /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
