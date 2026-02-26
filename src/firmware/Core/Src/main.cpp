#include "main.h"
#include "Controller.h"
#include "Motor.h"
#include "PID.h"
#include "adc.h"
#include "bno055.h"
#include "gpio.h"
#include "i2c.h"
#include "ms5611.h"
#include "tim.h"
#include "usb_device.h"
#include "usbd_cdc.h"

#include <cstdio>
#include <optional>
#include "array"


BNO055 bno;
MS5611 ms5611;

void move_motors(Motor motor_arr[8], float clamped_values[8]) {
    for (int i = 0; i < 8; i++)
        motor_arr[i].move(clamped_values[i]);
}

// yaw, angular yaw, pitch, angular pitch, roll, angular roll, depth, nullopt
std::array<std::optional<float>, 8> fetch_sensor_data(bool use_angle_rates) {
    std::array<std::optional<float>, 8> data;

    for (int i = 0; i < 6; i += 2)
        data[i] = bno.get_euler_angles
                      .angles[i]; // need to change the euler angles struct to contain array

    if (use_angle_rates) // eh lazmet this boolean?? law keda keda when i call this function i want
                         // the angle rates
        for (int i = 1; i < 7; i += 2)
            data[i] = bno.get_body_rates().body_rates[i]; // need to change the struct to contain an
                                                          // array so that we can iterate

    data[6] = ms5611.getDepth();

    return data; // 8aleban this is okay cuz std::array is a struct
}

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
    unsigned char control_byte; // depth pitch roll yaw //need to change the order 3ashan law hane3mel loop
    float data[6]; // Fx Fy Fz Froll Fpitch Fyaw
    float setpoint[4];
    float controller_output[6]; // depth pitch roll yaw surge sway

    float hold[4]; // yaw pirch roll depth

    /*Initialize all controllers*/
    Controller depth_pid(PID(0, 0, 0)); // lessa mtl3nash el values kp,ki,kd
    Controller pitch_pid(PID(0, 0, 0), std::optional(PID(0, 0, 0)));
    Controller roll_pid(PID(0, 0, 0), std::optional(PID(0, 0, 0)));
    Controller yaw_pid(PID(0, 0, 0), std::optional(PID(0, 0, 0)));

    float prev;
    float now = HAL_GetTick();

    std::array<std::optional<float>, 8> sensor_data;

    while (true) {

        RxPacket rx_pkt;
        TxPacket tx_pkt;
        switch (flow_state) {
        case FLOW_RECEIVING:
            if (data_received) {
                data_received = 0;
                memcpy(&rx_pkt, rx_buffer, sizeof(RxPacket));
                flow_state = FLOW_SENDING;
            } else {
                flow_state = FLOW_WAITING;  // no data received, signal Pi
            }
            break;

        case FLOW_WAITING:
            CDC_Transmit_FS(&ready_byte, 1);
            flow_state = FLOW_RECEIVING;
            break;

        case FLOW_SENDING:
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

        // read gui data
        // read sensor data

        // depth
        if (control_byte & 1 << 7) // setpoint
        {
            controller_output[0] = depth_pid.output(setpoint[0], depth, dt);
        }
        else {
            if (data[2] == 0) // hold position
            {
                controller_output[0] = depth_pid.output(hold_depth, depth, dt);
            }
            else // pilot command
            {
                controller_output[0] = data[2];
                hold_depth = depth;
            }
        }

        // pitch
        if (control_byte & 1 << 6) // setpoint
        {
            controller_output[1] = pitch_pid.output(setpoint[1], pitch, dt, pitch_rate);
        }
        else {
            if (data[4] == 0) // hold position
            {
                controller_output[1] = pitch_pid.output(hold_pitch, pitch, dt, pitch_rate);
            }
            else // pilot command
            {
                controller_output[1] = data[4];
                hold_pitch = pitch;
            }
        }

        // roll
        if (control_byte & 1 << 5) // setpoint
        {
            controller_output[2] = roll_pid.output(setpoint[2], roll, dt, roll_rate);
        }
        else {
            if (data[3] == 0) // hold position
            {
                controller_output[2] = roll_pid.output(hold_roll, roll, dt, roll_rate);
            }
            else // pilot command
            {
                controller_output[2] = data[3];
                hold_roll = roll;
            }
        }

        // yaw
        if (control_byte & 1 << 4) // setpoint
        {
            controller_output[3] = yaw_pid.output(setpoint[3], yaw, dt, yaw_rate);
        }
        else {
            if (data[5] == 0) // hold position
            {
                controller_output[3] = yaw_pid.output(hold_yaw, yaw, yaw_rate);
            }
            else // pilot command
            {
                controller_output[3] = data[5];
                hold_yaw = yaw;
            }
        }

        // surge
        controller_output[4] = data[0];
        // sway
        controller_output[5] = data[1];
    }
    float* clamped_motors = apply_pseudo_inverse(controller_output);
    move_motors(, clamped_motors);
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
