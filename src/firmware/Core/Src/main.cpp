#include "main.h"
#include "PID.h"
#include "adc.h"
#include "bno055.h"
#include "gpio.h"
#include "i2c.h"
#include "ms5611.h"
#include "tim.h"
#include "usb_device.h"

#include <cmath>
#include <cstdio>
#include <optional>
#include "Motor.h"
#include "array"


static constexpr float A_inv[8][6] = {{0.25, -0.25, 0.0, 0.0, 0.0, 0.25},
                                      {0.25, 0.25, 0.0, 0.0, 0.0, -0.25},
                                      {-0.25, 0.25, 0.0, 0.0, 0.0, 0.25},
                                      {-0.25, -0.25, 0.0, 0.0, 0.0, -0.25},

                                      {0.0, 0.0, 0.25, -0.25, 0.25, 0.0},
                                      {0.0, 0.0, 0.25, 0.25, 0.25, 0.0},
                                      {0.0, 0.0, 0.25, -0.25, -0.25, 0.0},
                                      {0.0, 0.0, 0.25, 0.25, -0.25, 0.0}};

BNO055 bno;
MS5611 ms5611;

void normalize_thrusters(float output[8], char* buffer);

// buffer must be of size 8
void apply_pseudo_inverse(const float v[6], float* buffer) {
    for (int i = 0; i < 8; i++) {
        buffer[i] = 0.0f;
        for (int j = 0; j < 6; j++)
            buffer[i] += A_inv[i][j] * v[j];
    }
}

void normalize_thrusters(float output[8]) { // TODO: to be reduced
    float maxH = 0;
    float maxV = 0;
    for (int i = 0; i < 4; i++) {
        float val = std::fabs(output[i]);
        if (val > maxH)
            maxH = val;
    }

    if (maxH > 1.0f)
        for (int i = 0; i < 4; i++)
            output[i] /= maxH;

    for (int i = 4; i < 8; i++) {
        float val = std::fabs(output[i]);
        if (val > maxV)
            maxV = val;
    }
    if (maxV > 1.0f)
        for (int i = 4; i < 8; i++)
            output[i] /= maxV;
}

struct Controller {
    explicit constexpr Controller(PID angle_pid, std::optional<PID> rate_pid = std::nullopt) :
        angle_pid(std::move(angle_pid)), rate_pid(std::move(rate_pid)) {}

private:
    PID angle_pid;
    std::optional<PID> rate_pid;

public:
    float output(float setpoint, float angle, float dt, std::optional<float> rate = std::nullopt) {
        if (rate) {
            const auto angle_pid_output = static_cast<float>(angle_pid.update(setpoint, angle, dt));
            return static_cast<float>(rate_pid->update(angle_pid_output, *rate, dt));
        }
        return static_cast<float>(angle_pid.update(setpoint, angle, dt));
    }
};

void move_motors(Motor motor_arr[8], float clamped_values[8]) {
    for (int i = 0; i < 8; i++)
        motor_arr[i].move(clamped_values[i]);
}


// depth,nullopt, roll, angular roll, pitch, angular pitch, yaw, angular yaw
std::array<std::optional<float>, 8> fetch_sensor_data(bool use_angle_rates) {
    std::array<std::optional<float>, 8> data;

    data[0] = ms5611.getDepth();
    data[1] = std::nullopt;
    data[2] = bno.euler_angles().x;
    data[3] = bno.get_body_rates().roll;
    data[4] = bno.euler_angles().y;
    data[5] = bno.get_body_rates().pitch;
    data[6] = bno.euler_angles().z;
    data[7] = bno.get_body_rates().yaw;

    return data;
}

void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void) {

    /* USER CODE BEGIN 1 */

    /* USER CODE END 1 */

    /* MCU
     * Configuration--------------------------------------------------------*/

    /* Reset of all peripherals, Initializes the Flash interface and the
     * Systick.
     */
    HAL_Init();

    /* USER CODE BEGIN Init */

    /* USER CODE END Init */

    /* Configure the system clock */
    SystemClock_Config();

    /* USER CODE BEGIN SysInit */

    /* USER CODE END SysInit */

    /* Initialize all configured peripherals */
    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_I2C3_Init();
    MX_TIM1_Init();
    MX_TIM2_Init();
    MX_TIM3_Init();
    MX_TIM4_Init();
    MX_TIM5_Init();
    MX_USB_DEVICE_Init();

    unsigned char control_byte; // depth roll pitch yaw
    float data[6]; // Fx Fy Fz Froll Fpitch Fyaw
    float setpoint[4]; // depth roll pitch yaw
    float controller_output[6]; // surge sway depth roll pitch yaw

    float hold[4]; // depth roll pitch yaw

    /*Initialize all controllers*/
    Controller controller[4] = {// lessa mtl3nash el values kp,ki,kd
                                Controller depth_pid(PID(0, 0, 0)),
                                Controller roll_pid(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
                                Controller pitch_pid(PID(0, 0, 0), std::optional(PID(0, 0, 0))),
                                Controller yaw_pid(PID(0, 0, 0), std::optional(PID(0, 0, 0)))};

    float prev;
    float now = HAL_GetTick();

    std::array<std::optional<float>, 8> sensor_data;

    while (true) {
        sensor_data = fetch_sensor_data();

        prev = now;
        now = HAL_GetTick();
        float dt = (now - prev) / 1000.0; // convert ms->seconds

        // read gui data
        // read sensor data

        for (int i = 0, j = 0; i < 8; i += 2, j++) {

            if (control_byte & 1 << (7 - j)) // setpoint
                controller_output[j + 2] =
                    controller[j].output(setpoint[j], sensor_data[i], dt, sensor_data[i + 1]);
            else {
                if (data[j + 2] == 0) // hold position
                    controller_output[j + 2] =
                        controller[j].output(hold[j], sensor_data[i], dt, sensor_data[i + 1]);
                else { // pilot command
                    controller_output[j + 2] = data[j + 2];
                    hold[j] = sensor_data[i];
                }
            }
        }

        // surge
        controller_output[0] = data[0];
        // sway
        controller_output[1] = data[1];
    }
    float* clamped_motors = apply_pseudo_inverse(
        controller_output); // fo2 8ayarna el function khalenaha void fa me7tageen ne8ayar dah
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
