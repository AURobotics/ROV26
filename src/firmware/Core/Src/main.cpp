#include "main.h"
#include "PID.h"
#include "adc.h"
#include "gpio.h"
#include "i2c.h"
#include "tim.h"
#include "usb_device.h"
#include "bno055.h"
#include "ms5611.h"

#include <cmath>
#include <cstdio>
#include <optional>

float output[8];
float A_inv[8][6] = {
    {0.25, -0.25, 0.0, 0.0, 0.0, 0.25}, {0.25, 0.25, 0.0, 0.0, 0.0, -0.25}, {-0.25, 0.25, 0.0, 0.0, 0.0, 0.25}, {-0.25, -0.25, 0.0, 0.0, 0.0, -0.25},

    {0.0, 0.0, 0.25, -0.25, 0.25, 0.0},
    {0.0, 0.0, 0.25, 0.25, 0.25, 0.0},
    {0.0, 0.0, 0.25, -0.25, -0.25, 0.0},
    {0.0, 0.0, 0.25, 0.25, -0.25, 0.0}};

float *normalize_thrusters(float output[8]);

float *multiply_matrix(float V[6])
{
  for (int i = 0; i < 8; i++)
  {
    output[i] = 0.0f;
    for (int j = 0; j < 6; j++)
    {
      output[i] += A_inv[i][j] * V[j];
    }
  }
  return normalize_thrusters(output);
}

float *normalize_thrusters(float output[8])
{
  float maxH = 0.0f;
  float maxV = 0.0f;
  for (int i = 0; i < 4; i++)
  {
    float val = fabs(output[i]);
    if (val > maxH)
    {
      maxH = val;
    }
  }
  if (maxH > 1.0f)
  {

    for (int i = 0; i < 4; i++)
    {
      output[i] /= maxH;
    }
  }

  for (int i = 4; i < 8; i++)
  {
    float val = fabs(output[i]);
    if (val > maxV)
    {
      maxV = val;
    }
  }
  if (maxV > 1.0f)
  {

    for (int i = 4; i < 8; i++)
    {
      output[i] /= maxV;
    }
  }
  return output;
}

struct Controller
{
  explicit constexpr Controller(const PID &angle_pid,
                                const std::optional<PID> &rate_pid = std::nullopt)
      : angle_pid(angle_pid), rate_pid(rate_pid) {}

private:
  PID angle_pid;
  std::optional<PID> rate_pid = std::nullopt;

public:
  float output(float setpoint, float angle, float dt,
               std::optional<float> rate = std::nullopt)
  {
    float angle_pid_output;
    if (rate)
    {
      angle_pid_output = angle_pid.update(setpoint, angle, dt);
      return rate_pid->update(angle_pid_output, *rate, dt);
    }

    else
      return angle_pid.update(setpoint, angle, dt);
  }
};

void move_motors(Motor motor_arr[8], float clamped_values[8])
{
  for (int i = 0; i < 8; i++)
  {
    motor_arr[i].drive(clamped_values[i]);
  }
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
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick.
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

  byte control_byte; // depth pitch roll yaw
  float data[6];     // Fx Fy Fz Froll Fpitch Fyaw// forces in the axis//probably need something else bec its confusing
  float setpoint[4];
  float controller_output[6]; // depth pitch roll yaw surge sway

  float hold_depth;
  float hold_yaw;
  float hold_pitch;
  float hold_roll;

  /*Initialize all pids*/
  Controller depth_pid(PID(kp, ki, kd)); // lessa mtl3nash el values kp,ki,kd
  Controller pitch_pid(PID(kp, ki, kd), PID(kp, ki, kd));
  Controller roll_pid(PID(kp, ki, kd), PID(kp, ki, kd));
  Controller yaw_pid(PID(kp, ki, kd), PID(kp, ki, kd));

  float depth, yaw, pitch, roll; // read from sensors
  float yaw_rate, pitch_rate, roll_rate;
  float prev;
  float now = HAL_GetTick();

  while (1)
  {
    depth = getDepth();
    pitch = get_euler_angles().pitch;
    yaw = get_euler_angles().yaw;
    roll = get_euler_angles().roll;

    yaw_rate = get_body_rates().z;
    pitch_rate = get_body_rates().y;
    roll_rate = get_body_rates().x;

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
    else
    {
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
    else
    {
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
    else
    {
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
    else
    {
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
  float *clamped_motors = multiply_matrix(controller_output);
  move_motors(, clamped_motors);
}

/**
 * @brief System Clock Configuration
 * @retval None
 */
void SystemClock_Config(void)
{
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
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
   */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
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
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
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
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line
     number, ex: printf("Wrong parameters value: file %s on line %d\r\n", file,
     line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
