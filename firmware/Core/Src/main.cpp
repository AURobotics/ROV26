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
enum class Test_state { OFF, TUNING_MODE, DONE };

#define WR_ALL_REGS(_regs_, _data_)                                                                                    \
    do                                                                                                                 \
        for (size_t addr = 0; addr < sizeof(_regs_) / sizeof((_regs_)[0]); addr++)                                     \
            (_regs_)[addr] = (_data_);                                                                                 \
    while (0)

MS5611 ms5611(&hi2c3);
Cdc_driver cdc(20); /*need to set timeout*/

extern "C" int _write(int file, char* ptr, int len) {
    CDC_Transmit_FS((uint8_t*)ptr, len);
    return len;
}

// depth, nullopt, roll, angular roll, pitch, angular pitch, yaw, angular yaw,
void fetch_sensor_data(std::array<std::optional<float>, 8>& data) {
    if (HAL_GetTick() - ms5611.last_read_time > 100) {
        data[0] = ms5611.getPressure();
        data[1] = std::nullopt;
    }

    u_long _now = HAL_GetTick();
    static u_long _last_time = _now;
    if (_now - _last_time >= 5) {
        _last_time = _now;
        get_mpu_data();
        get_ak_data();
    }

    _now = HAL_GetTick();
    static auto last_filter_time = static_cast<float>(_now);
    float dt = static_cast<float>(_now) - last_filter_time;
    if (dt >= 1) {
        last_filter_time = _now;
        MadgwickAHRSupdate(dt * 0.001f,
                           MPU9250.gx,
                           MPU9250.gy,
                           MPU9250.gz,
                           MPU9250.ax,
                           MPU9250.ay,
                           MPU9250.az,
                           MPU9250.my,
                           MPU9250.mx,
                           -1.0f * MPU9250.mz);
        computeAngles();
        data[2] = roll;
        data[3] = MPU9250.gx;
        data[4] = pitch;
        data[5] = MPU9250.gy;
        data[6] = yaw;
        data[7] = MPU9250.gz;
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

float angle_diff(float setpoint, float current) {
    float diff = setpoint - current;
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

static void gripper_up() {
    HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_SET);
    HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_RESET);
}
static void gripper_down() {
    HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_SET);
}

static void gripper_stop() {
    HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_RESET);
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
            HAL_GPIO_WritePin(LED_FLASHER_GPIO_Port, LED_FLASHER_Pin, LedState ? GPIO_PIN_SET : GPIO_PIN_RESET);
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

    HAL_NVIC_SetPriority(IRQn_Type::OTG_FS_IRQn, 1, 0);
    HAL_NVIC_SetPriority(IRQn_Type::OTG_FS_WKUP_IRQn, 1, 0);
    HAL_NVIC_SetPriority(IRQn_Type::I2C3_ER_IRQn, 1, 0);
    HAL_NVIC_SetPriority(IRQn_Type::I2C3_EV_IRQn, 1, 0);
    HAL_NVIC_SetPriority(IRQn_Type::SysTick_IRQn, 0, 0);

    HAL_Delay(2000);

    Test_state test_state{}; // normal mode
    //////Testing Mode////////
    float start_yaw = 0;
    float max_testing[4] = {1, 40, 40, 90}; // need to set these

    /////sending to GUI/////
    uint32_t last_send_time = 0;

    //////Controller////
    float prev_controller_time{}; // to calculate dt
    uint32_t now = HAL_GetTick();

    float forces[6]; // Fx Fy Fz Froll Fpitch Fyaw

    float controller_output[6];
    float motors_buffer[8]= {};
    float last_received_setpoints[4]; // depth roll pitch yaw

    /*Initialize all controllers: depth roll pitch yaw*/
    Controller controller[4] = {Controller(PID(0, 0, 0)),
                                Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
                                Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
                                Controller(PID(0, 0, 0), std::optional(PID(0, 0, 0)))};

    Motor motors[] = {Motor({&htim1, TIM_CHANNEL_2}, {&htim1, TIM_CHANNEL_3}),
                      Motor({&htim3, TIM_CHANNEL_4}, {&htim2, TIM_CHANNEL_3}),
                      Motor({&htim3, TIM_CHANNEL_3}, {&htim3, TIM_CHANNEL_2}),
                      Motor({&htim3, TIM_CHANNEL_1}, {&htim2, TIM_CHANNEL_1}),
                      Motor({&htim5, TIM_CHANNEL_3}, {&htim5, TIM_CHANNEL_2}),
                      Motor({&htim4, TIM_CHANNEL_4}, {&htim4, TIM_CHANNEL_3}),
                      Motor({&htim4, TIM_CHANNEL_1}, {&htim4, TIM_CHANNEL_2}),
                      Motor({&htim5, TIM_CHANNEL_4}, {&htim2, TIM_CHANNEL_2})};

    for (auto& motor : motors)
        motor.setup();

    for (int i = 4; i < 8; i++) {
        if (i==6) continue;
        motors[i].move(1);
    }

    HAL_Delay(2000);
    for (int i = 4; i < 8; i++) {
        motors[i].move(0);
    }


    std::array<std::optional<float>, 8> sensor_data;


    Generic_msg received_msg{};

    // ms5611.begin();
    // MPU9250_init();

    Ready_msg ready_msg{.sync_byte = 255, .type = READY_MESSAGE};

    while (!cdc.available()) {
        cdc.write_msg(ready_msg);
        HAL_Delay(100);
    }

    // ReSharper disable once CppDFAEndlessLoop
    while (true) {
        if (cdc.available()) {
            cdc.read_msg(received_msg);
            HAL_Delay(1);
            cdc.write_msg(ready_msg);
        }

        if (HAL_GetTick() - cdc.last_received_time > 100) {
            gripper_stop();
            for (auto& motor : motors)
                motor.stop();
            while (!cdc.available()) {
                cdc.write_msg(ready_msg);
                HAL_Delay(100);
            }
        }

        for (int i = 0; i < 5; i++) {
            forces[i] = received_msg.data.command_msg.forces[i] * 4;
        }
        apply_pseudo_inverse(forces, motors_buffer);
        normalize_thrusters(motors_buffer);

        for (int i = 0; i < 8; i++) {
            if (i == 7) continue;
            motors[i].move(motors_buffer[i]);
        }


        continue;
        if (cdc.last_received_msg_type == OPERATION_MESSAGE)
            test_state = received_msg.data.operation_msg.operation_mode ? Test_state::TUNING_MODE : Test_state::OFF;

        fetch_sensor_data(sensor_data);

        if (test_state == Test_state::OFF) // Normal mode
        {
            if (cdc.last_received_msg_type == COMMAND_MESSAGE) {
                const auto control_byte = received_msg.data.command_msg.control_byte;

                prev_controller_time = now;
                now = HAL_GetTick();
                float dt = (now - prev_controller_time) / 1000.0;

                for (int i = 0, j = 0; i < 8; i += 2, j++)
                    if (control_byte & 1 << (15 - j)) { // setpoint
                        if (j > 0) // angle
                            controller_output[j + 2] = controller[j].output(
                                angle_diff(forces[j + 2], sensor_data[i].value()), 0, dt, sensor_data[i + 1].value());

                        else // depth
                            controller_output[j + 2] = controller[j].output(
                                forces[j + 2], sensor_data[i].value(), dt, sensor_data[i + 1].value());
                    }
                    else {
                        if (forces[j + 2] == 0) // hold position
                            controller_output[j + 2] = controller[j].output(
                                last_received_setpoints[j], sensor_data[i].value(), dt, sensor_data[i + 1].value());
                        else { // pilot command
                            controller_output[j + 2] = forces[j + 2] * 4;
                            last_received_setpoints[j] = sensor_data[i].value();
                        }
                    }

                // surge, x
                controller_output[0] = forces[0] * 4;
                // sway, y
                controller_output[1] = forces[1] * 4;
                // grippers
                HAL_GPIO_WritePin(
                    DCV_1_GPIO_Port, DCV_1_Pin, word_read(control_byte, DCVS) ? GPIO_PIN_SET : GPIO_PIN_RESET);
                HAL_GPIO_WritePin(DCV_2_GPIO_Port,
                                  DCV_2_Pin,
                                  word_read(control_byte, static_cast<Control_byte_bit_mask>(DCVS + 1))
                                      ? GPIO_PIN_SET
                                      : GPIO_PIN_RESET);

                if (word_read(control_byte, ROT_GRP_EN))
                    word_read(control_byte, ROT_GRP_EN)
                        ? word_read(control_byte, ROT_GRP_DIR) ? gripper_up() : gripper_down()
                        : gripper_stop();
                else
                    gripper_stop();

                HAL_GPIO_WritePin(LED_FLASHER_GPIO_Port,
                                  LED_FLASHER_Pin,
                                  word_read(control_byte, LED) ? GPIO_PIN_SET : GPIO_PIN_RESET);
            }

            apply_pseudo_inverse(controller_output, motors_buffer);
            Motor::move_array(motors, motors_buffer);
        }

        else { // Testing mode
            static uint8_t test_axis = 0;
            if (cdc.last_received_msg_type == TUNING_MESSAGE) {
                test_axis = received_msg.data.tuning_msg.axis;
                if (test_axis == 3)
                    start_yaw = sensor_data[test_axis].value();
                test_state = Test_state::TUNING_MODE;
            }

            if (test_state == Test_state::TUNING_MODE) {
                Step_response_msg response{};
                for (float& i : controller_output)
                    i = 0; // make sure that other axes are off
                controller_output[test_axis + 2] = 0.4; // any constant value

                if (test_axis) {
                    if (angle_diff(sensor_data[test_axis * 2].value(), start_yaw) >= max_testing[test_axis]) {
                        controller_output[test_axis + 2] = 0;
                        test_state = Test_state::DONE;
                    }
                    response.sync_byte = 0xFF;
                    response.type = 6;
                    // response.timestamp=
                    response.angle = sensor_data[test_axis * 2].value();
                    response.angle_rate = sensor_data[(test_axis * 2) + 1].value();
                    // cdc.write_msg()
                }
                else if (!test_axis) {
                    if (sensor_data[test_axis * 2].value() >= max_testing[test_axis]) {
                        response.sync_byte = 0xFF;
                        response.type = 6;
                        response.angle = sensor_data[test_axis * 2].value();
                        response.angle_rate = NULL;
                        // response.timestamp
                        // cdc.write_msg()
                    }
                }

                if (sensor_data[test_axis * 2].value() >= max_testing[test_axis]) {
                    controller_output[test_axis + 2] = 0;
                    test_state = Test_state::DONE;
                }
            }

            if (test_state == Test_state::DONE && cdc.last_received_msg_type == Message_Type::PARAMETERS_MESSAGE) {
                if (received_msg.data.param_msg.pid_type) // angle pid
                    controller[test_axis].set_angle_pid(
                        received_msg.data.param_msg.Kp, received_msg.data.param_msg.ki, received_msg.data.param_msg.kd);
                else // rate pid
                    controller[test_axis].set_rate_pid(
                        received_msg.data.param_msg.Kp, received_msg.data.param_msg.ki, received_msg.data.param_msg.kd);
                test_state = Test_state::OFF;
            }
        }


        ///////////////////send data to GUI/////////////////////
        static Sensor_msg sensor_message{.sync_byte = 255, .type = Message_Type::SENSOR_MESSAGE}; // 3amlin enum zina

        if (HAL_GetTick() - last_send_time >= 20) {
            // motor telemetry
            sensor_message.status = loadStatus();
            sensor_message.depth = sensor_data[0].value();
            sensor_message.pitch = sensor_data[4].value();
            sensor_message.roll = sensor_data[2].value();
            sensor_message.yaw = sensor_data[6].value();

            for (int i = 0; i < 8; i++) {
                sensor_message.motor_speeds[i] = motors_buffer[i];
            }
            cdc.write_msg(sensor_message);
            last_send_time = HAL_GetTick();
        }

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
    RCC_OscInitStruct.PLL.PLLN = 336;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
    RCC_OscInitStruct.PLL.PLLQ = 7;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        Error_Handler();
    }

    /** Initializes the CPU, AHB and APB buses clocks
     */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
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
