#include "main.h"
#include "Cdc_driver.h"
#include "Controller.h"
#include "Motor.h"
#include "PID.h"
#include "adc.h"
#include "gpio.h"
#include "mpu9250.h"
#include "ms5611.h"
#include "pwm.h"
#include "tim.h"
#include "usb_comms.h"
#include "usb_device.h"
extern "C" {
#include "i2c.h"
}
#include <cmath>
#include <optional>
#include "Kinematics.h"
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

MPU9250 mpu9250(&hi2c3);
//MS5611 ms5611(&hi2c3);
Cdc_driver cdc(20); /*need to set timeout*/

extern "C" int _write(int file, char *ptr, int len){
CDC_Transmit_FS((uint8_t*)ptr, len);
return len;
}

// yaw, angular yaw, pitch, angular pitch, roll, angular roll, depth, nullopt
void fetch_sensor_data(std::array<std::optional<float>, 8>& data) {
    //if (HAL_GetTick() - ms5611.last_read_time > 0.5) {
      //  data[0] = ms5611.getDepth();
      //  data[1] = std::nullopt;
    //}

    if (HAL_GetTick() - mpu9250.last_read_time > 5) {
        mpu9250.update();
        vec_3 angles = mpu9250.getEulerAngles();
        vec_3 rates = mpu9250.getBodyRates();

        data[2] = angles.x(); // roll
        data[3] = 0 ;//rates.x();
        data[4] = angles.y(); // pitch
        data[5] = 0; //rates.y();
        data[6] = angles.z(); // yaw
        data[7] = 0; //rates.z();
    }
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
    ADC_ChannelConfTypeDef sConfig = {};
    sConfig.Channel = channel;
    sConfig.Rank = 1;
    sConfig.SamplingTime =
        ADC_SAMPLETIME_84CYCLES; // sampling time is 84 cycles, which is 84/84MHz = 1us
    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
        return 0u;

    HAL_ADC_Start(&hadc1);
    if (HAL_ADC_PollForConversion(&hadc1, 10) != HAL_OK)
        return 0u;
    uint32_t value = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    return value;
}

static void GripperOpen() {
    HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_RESET);
}
static void GripperClose() {
    HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_SET);
}

static uint8_t loadStatus() {
    uint8_t statusByte = 0;
    GPIO_PinState ledState = HAL_GPIO_ReadPin(LED_FLASHER_GPIO_Port, LED_FLASHER_Pin);

   uint16_t leakage_adc1 = (uint16_t)read_adc(LEAKAGE_ADC_CHANNEL_1);
    uint16_t leakage_adc2 = (uint16_t)read_adc(LEAKAGE_ADC_CHANNEL_2);
    bool leak_detected = leakage_adc1>LEAKAGE_THRESHOLD || leakage_adc2>LEAKAGE_THRESHOLD;


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

    Test_state test_state = Test_state::OFF; // normal mode
    //////Testing Mode////////
    float start_yaw = 0;
    float max_testing[4] = {0.1, 30, 30, 90}; // need to set these
    uint8_t test_axis = 0;

    /////sending to GUI/////
    uint32_t last_send_time = 0;

    //////Controller////
    float prev{}; // to calculate dt
    uint32_t now = HAL_GetTick();

    float data[6]; // Fx Fy Fz Froll Fpitch Fyaw
                   // if control bit = 1 setpoint hatetba3at makan
                   // el force fa will use this array as setpoint too
    float controller_output[6]; // surge sway depth roll pitch yaw
    float hold[4]; // depth roll pitch yaw

    /*Initialize all controllers: depth roll pitch yaw*/
    //Controller controller[4] = {Controller(PID(0, 0, 0)),
    //                            Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
    //                            Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
    //                            Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0)))};

    /*Intialize pwms  and motors*/
    // Create PWM wrappers
    PWM pwm1A(&htim1, TIM_CHANNEL_2);
    PWM pwm1B(&htim1, TIM_CHANNEL_3);

    PWM pwm2A(&htim3, TIM_CHANNEL_4);
    PWM pwm2B(&htim2, TIM_CHANNEL_3);

    PWM pwm3A(&htim3, TIM_CHANNEL_3);
    PWM pwm3B(&htim3, TIM_CHANNEL_2);

    PWM pwm4A(&htim3, TIM_CHANNEL_1);
    PWM pwm4B(&htim2, TIM_CHANNEL_1);

    PWM pwm5A(&htim5, TIM_CHANNEL_3);
    PWM pwm5B(&htim5, TIM_CHANNEL_2);

    PWM pwm6A(&htim4, TIM_CHANNEL_4);
    PWM pwm6B(&htim4, TIM_CHANNEL_3);

    PWM pwm7A(&htim4, TIM_CHANNEL_1);
    PWM pwm7B(&htim4, TIM_CHANNEL_2);

    PWM pwm8A(&htim5, TIM_CHANNEL_4);
    PWM pwm8B(&htim2, TIM_CHANNEL_2);


    Motor motors[] = {Motor(&pwm1A, &pwm1B),
                      Motor(&pwm2A, &pwm2B),
                      Motor(&pwm3A, &pwm3B),
                      Motor(&pwm4A, &pwm4B),
                      Motor(&pwm5A, &pwm5B),
                      Motor(&pwm6A, &pwm6B),
                      Motor(&pwm7A, &pwm7B),
                      Motor(&pwm8A, &pwm8B)};

    for (const auto& motor : motors)
        motor.setup();

    Motor gripper( // TODO: use this variable
        [](float speed)
        {
            if (speed > 0.1f) {
                HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
                HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_RESET);
            }
            else if (speed < -0.1f) {
                HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
                HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_SET);
            }
            else {
                HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
                HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_RESET);
            }
        });

    std::array<std::optional<float>, 8> sensor_data;
    TxPacket tx_pkt;
    tx_pkt.type = SENSOR_MESSAGE;
    GenericMessage msg{};
    float clamped_motors[8] = {};

    //__HAL_TIM_SET_COMPARE(&htim1,2,0);

    mpu9250.init();
    //ms5611.begin();

    // ReSharper disable once CppDFAEndlessLoop
    while (true) {
        static Message_Type msg_type;
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
//HAL_Delay(2500);
	//}

        fetch_sensor_data(sensor_data);


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
     //   HAL_GPIO_WritePin(DCV_1_GPIO_Port,
     //                     DCV_1_Pin,
     //                     GPIO_PIN_RESET);



     //   HAL_GPIO_WritePin(DCV_2_GPIO_Port,
     //                     DCV_2_Pin,
     //                     GPIO_PIN_RESET);

        // }

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
        static TxPacket feedback_pkt;

        if (HAL_GetTick() - last_send_time >= 50) {
            last_send_time = HAL_GetTick();

            feedback_pkt.sync_byte = 0xFF;
            feedback_pkt.type = 0x01;
            feedback_pkt.status = loadStatus();

            // sensor telemetry
            feedback_pkt.depth = sensor_data[0].value_or(0.0f);
            feedback_pkt.roll = sensor_data[2].value_or(0.0f);
            feedback_pkt.pitch = sensor_data[4].value_or(0.0f);
            feedback_pkt.yaw = sensor_data[6].value_or(0.0f);

            // motor telemetry
        //    for (int i = 0; i < 8; i++) {
        //        feedback_pkt.motor_speeds[i] = clamped_motors[i] * 255.0f;
        //    }

        //cdc.write_msg(&feedback_pkt);

            printf("\n\ryaw = %d, pitch = %d, roll = %d",(uint32_t)feedback_pkt.yaw,(uint32_t)feedback_pkt.pitch,(uint32_t)feedback_pkt.roll);

        }
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
