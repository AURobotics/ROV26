#include "main.h"
#include "Cdc_driver.h"
#include "Controller.h"
#include "Motor.h"
#include "PID.h"
#include "adc.h"
#include "gpio.h"
#include "mpu9250.h"
#include "ms5611.h"
#include "tim.h"
#include "usb_comms.h"
#include "usb_device.h"
extern "C" {
#include "i2c.h"
}
#include <cmath>
#include <optional>
#include "Kinematics.h"
#include "Madgwick_filter.h"
#include "array"
#include "main.h"
#include "usbd_cdc_if.h"

static constexpr int16_t LEAKAGE_THRESHOLD = 0;
enum class Test_state { OFF, STEPPING, DONE };

#define WR_ALL_REGS(_regs_, _data_)                                                                \
    do                                                                                             \
        for (size_t addr = 0; addr < sizeof(_regs_) / sizeof((_regs_)[0]); addr++)                 \
            (_regs_)[addr] = (_data_);                                                             \
    while (0)

// MS5611 ms5611(&hi2c3);
Cdc_driver cdc(20); /*need to set timeout*/

extern "C" int _write(int file, char* ptr, int len) {
    CDC_Transmit_FS((uint8_t*)ptr, len);
    return len;
}


double normalize_angle(double angle) {
    angle = fmod(angle, 360.0);
    if (angle > 180.0)
        angle -= 360.0;
    else if (angle < 180.0)
        angle += 360.0;

    return angle;
}

double angle_diff(double setpoint, double current) {
    double diff = setpoint - current;
    return normalize_angle(diff);
}

static uint32_t read_adc(uint32_t channel) {
    HAL_ADC_Stop(&hadc1);

    ADC_ChannelConfTypeDef sConfig = {};
    sConfig.Channel = channel;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_84CYCLES;

    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
        return 0;
    if (HAL_ADC_Start(&hadc1) != HAL_OK)
        return 0;
    if (HAL_ADC_PollForConversion(&hadc1, 10) != HAL_OK) {
        HAL_ADC_Stop(&hadc1);
        return 0;
    }
    uint32_t value = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    return value;
}

static void GripperUp() {
    HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_RESET);
}
static void GripperDown() {
    HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_SET);
}

static uint8_t loadStatus() {
    uint8_t statusByte = 0;
    const GPIO_PinState ledState = HAL_GPIO_ReadPin(LED_FLASHER_GPIO_Port, LED_FLASHER_Pin);

    const auto leakage_adc1 = read_adc(LEAKAGE_ADC_CHANNEL_1);
    const auto leakage_adc2 = read_adc(LEAKAGE_ADC_CHANNEL_2);
    const bool leak_detected = leakage_adc1 > LEAKAGE_THRESHOLD || leakage_adc2 > LEAKAGE_THRESHOLD;


    if (ledState == GPIO_PIN_SET)
        statusByte |= (1 << 2);

    if (leak_detected)
        statusByte |= (1 << 3);

    // if (gripper_safety_enabled)
    //     statusByte |= (1 << 4);
    //
    // if (leakage_safety_enabled)
    //     statusByte |= (1 << 5);

    return statusByte;
}
// End of gripper limit switch

// communication loss
#define TIMEOUT_MS 100U // ms of silence before declaring comms lost
#define BLINK_MS 250U // ms for toggling LED to indicate comms loss
volatile uint32_t lastCommsTime = 0;

static void StopMotors(Motor motor_arr[8]) {
    // GripperStop();
    for (int i = 0; i < 7; i++)
        motor_arr[i].stop();
}

static void checkCommsTimeout() {
    static bool CommsLostPrev = false; // tracks previous state for edge detection
    static uint32_t BlinkTick = 0; // last LED toggle time
    static bool LedState = false;
    uint32_t now = HAL_GetTick();
    bool commsLost = now - lastCommsTime > TIMEOUT_MS;
    if (commsLost) {
        if (!CommsLostPrev) {
            // Comms timeout --> stop all motors and indicate loss of comms
            // StopMotors(); //TODO
        }
        if (now - BlinkTick >= BLINK_MS) {
            LedState = !LedState;
            HAL_GPIO_WritePin(
                LED_FLASHER_GPIO_Port, LED_FLASHER_Pin, LedState ? GPIO_PIN_SET : GPIO_PIN_RESET);
            BlinkTick = now;
        }
    }
    else {
        LedState = false;
        HAL_GPIO_WritePin(LED_FLASHER_GPIO_Port, LED_FLASHER_Pin, GPIO_PIN_RESET);
    }
    CommsLostPrev = commsLost;
}

// End of communication loss
void SystemClock_Config();
/* USER CODE BEGIN PFP */

void checkDFUmode() {
    if (dfu_flag == MAGIC_DFU) {
        dfu_flag = 0; // clear flag to prevent looping
        // jump to system memory bootloader
        void (*SysMemBootJump)(void);
        uint32_t sysmem_start = 0x1FFF0000; // STM32F1/F4 example, varies per series
        SysMemBootJump = (void (*)(void))(*((uint32_t*)(sysmem_start + 4)));

        __set_MSP(*(__IO uint32_t*)sysmem_start);
        SysMemBootJump();
    }
}
/**
 * @brief  The application entry point.
 * @retval int
 */
int main() {
    checkDFUmode();

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

    HAL_Delay(2000);
    printf("code started\n");

    uint8_t UART_tx_buffer[100];
    uint8_t length;
    printf("\r%d\r\n",MPU9250_init());
    // ReSharper disable once CppDFAEndlessLoop

    while (true) {
        get_mpu_data();
        get_ak_data();
        MadgwickAHRSupdate(MPU9250.gx,
                           MPU9250.gy,
                           MPU9250.gz,
                           MPU9250.ax,
                           MPU9250.ay,
                           MPU9250.az,
                           MPU9250.my,
                           MPU9250.mx,
                           -MPU9250.mz);
        computeAngles();
        u_long now = HAL_GetTick();
        static u_long last_time = now;
        if (now - last_time > 100) {
            last_time = now;
            length = sprintf((char*)UART_tx_buffer, "Orientation: %f %f %f\r\n", yaw, pitch, roll);
            CDC_Transmit_FS(UART_tx_buffer, length);
        }
        HAL_Delay(1);
        //  if (cdc.available()) {
        //      msg_type = cdc.read_msg(msg);

        //  }
        //  if (msg_type == OPERATION_MESSAGE)
        //      test_state =
        //          msg.data.operation_msg.operation_mode ? Test_state::STEPPING : Test_state::OFF;

        //  if (test_state == Test_state::OFF) {
        //      if (msg_type == COMMAND_MESSAGE) {
        //          for (int i = 0; i < 6; i++)
        //              controller_output[i] = msg.data.command_msg.forces[i] * 4;
        // apply_pseudo_inverse(controller_output, clamped_motors);
        // Motor::move_motor(motors, clamped_motors);
        //      }
        //  }fetch
        //    int num = 6;
        //    float arr[8] = {0.6, 0,0,0,0,0,0,0};
        //    float v[num] = {1,0,0,0,0,0};
        //   apply_pseudo_inverse(v,arr);

        // Motor::move_motor(motors,arr);
        // motors[2].move(-0.75);

        //	for (int i = 0; i < 8; i ++) {
        //		motors[i].move(0.75);
        //		HAL_Delay(2500);
        //		motors[i].move(-0.75);
        //		HAL_Delay(2500);
        //		motors[i].move(0);
        // HAL_Delay(2500);
        //}


        // GripperUp();
        // HAL_Delay(2000);
        // GripperDown();
        //  HAL_Delay(2000);

        // if (data_received_flag) {
        //     data_received_flag = 0;
        //     CDC_Transmit_FS(reinterpret_cast<uint8_t*>(&ready_msg), sizeof(Ready_Msg));
        //     // process_data(data_type) // idk do something.
        //     // depends on type of message do something.
        //     // if default message -> change global variable which hold setpoints.
        //     // if parameters message -> got set parameters.
        //     // if operation mode (normal operation or tuning / testing) -> change global state.
        //     // if no new message received for 100ms -> stop all motors (different than
        //     // timeout(40ms)) and blink leds in a pattern if new data -> then set the new data if
        //     no
        //     // new data -> just output pid without setpoints suggestions: in main loop, read
        //     sensor
        //     // data and process pid, if setpoint changes then
        // }
        // else
        //     // CDC_Transmit_FS(reinterpret_cast<uint8_t*>(&ready_msg), sizeof(Ready_Msg));


        // if (test_state == TEST_STATE::OFF) // Normal mode
        // {
        //     if(msg_type == COMMAND_MESSAGE)
        //     {
        //         const unsigned char control_byte = msg.control_byte;
        //         for (int i = 0; i < 6; i++)
        //             data[i] = msg.forces[i]*4;

        //         prev = now;
        //         now = HAL_GetTick();
        //         float dt = (now - prev) / 1000.0; // convert ms->seconds

        //         for (int i = 0, j = 0; i < 8; i += 2, j++)
        //             if (control_byte & 1 << (7 - j)) { // setpoint
        //                 if (j > 0) // not depth
        //                     controller_output[j + 2] =
        //                         controller[j].output(angle_diff(data[j + 2],
        //                         sensor_data[i].value()),
        //                                              0,
        //                                              dt,
        //                                              sensor_data[i + 1]);

        //                 else // depth
        //                     controller_output[j + 2] = controller[j].output(
        //                         data[j + 2], sensor_data[i].value(), dt, sensor_data[i +
        //                         1].value());
        //             }
        //             else {
        //                 if (data[j + 2] == 0) // hold position
        //                     controller_output[j + 2] = controller[j].output(
        //                         hold[j], sensor_data[i].value(), dt, sensor_data[i + 1].value());
        //                 else { // pilot command
        //                     controller_output[j + 2] = data[j + 2];
        //                     hold[j] = sensor_data[i].value();
        //                 }
        //             }

        //         // surge
        //         controller_output[0] = data[0]*4;
        //         // sway
        //         controller_output[1] = data[1]*4;
        //     }
        //
        // HAL_GPIO_WritePin(DCV_1_GPIO_Port,
        //                DCV_1_Pin,
        //                GPIO_PIN_RESET);


        //        HAL_GPIO_WritePin(DCV_2_GPIO_Port,
        //                         DCV_2_Pin,
        //                    GPIO_PIN_RESET);


        //  HAL_Delay(2000);
        //  HAL_GPIO_WritePin(DCV_1_GPIO_Port,
        //              DCV_1_Pin,
        //              GPIO_PIN_SET);


        // HAL_GPIO_WritePin(DCV_2_GPIO_Port,
        //                    DCV_2_Pin,
        //                 GPIO_PIN_SET);
        // HAL_Delay(2000);


        // else { // Testing mode
        //     if (last_received_msg_type == TUNING_MESSAGE && test_state == Test_state::OFF) {
        //         test_axis = tuning_msg.axis;
        //         if (test_axis == 3)
        //             start_yaw = sensor_data[test_axis].value();
        //         test_state = Test_state::STEPPING;
        //     }
        //
        //     if (test_state == Test_state::STEPPING) {
        //         for (float& i : controller_output)
        //             i = 0; // make sure that other axes are off
        //         controller_output[test_axis + 2] = 0.4; // any constant value
        //
        //         if (test_axis == 3) { // yaw
        //             if (angle_diff(sensor_data[test_axis].value(), start_yaw) >=
        //                 max_testing[test_axis]) {
        //                 controller_output[test_axis + 2] = 0;
        //                 test_state = Test_state::DONE;
        //             }
        //         }
        //         else if (sensor_data[test_axis].value() >= max_testing[test_axis]) {
        //             controller_output[test_axis + 2] = 0;
        //             test_state = Test_state::DONE;
        //         }
        //     }
        //
        //     if (test_state == Test_state::DONE &&
        //         last_received_msg_type == Message_Type::PARAMETERS_MESSAGE) {
        //         if (param_msg.pid_type) // angle pid
        //             controller[test_axis].set_angle_pid(param_msg.Kp, param_msg.ki,
        //             param_msg.kd);
        //         else // rate pid
        //             controller[test_axis].set_rate_pid(param_msg.Kp, param_msg.ki, param_msg.kd);
        //
        //         test_state = Test_state::OFF;
        //     }
        // }
        //

        ///////////////////send data to GUI/////////////////////


        // motor telemetry
        //    for (int i = 0; i < 8; i++) {
        //        feedback_pkt.motor_speeds[i] = clamped_motors[i] * 255.0f;
        //    }

        // cdc.write_msg(&feedback_pkt);


        // }
    }
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
    /* User can add his own implementation to report the HAL error return state */
    MX_USB_DEVICE_Init();
    printf("inside error handling");
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
       number, ex: printf("Wrong parameters value: file %s on line %d\r\n", file,
       line) */
    /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
