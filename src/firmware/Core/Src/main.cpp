#include "main.h"
#include "PID.h"
#include "adc.h"
#include "gpio.h"
#include "i2c.h"
#include "tim.h"
#include "usb_device.h"

#include <cmath>
#include <cstdio>
#include <optional>

float output[8];
float A_inv[8][6] = {
    {0.25, -0.25, 0.0, 0.0, 0.0, 0.25},  {0.25, 0.25, 0.0, 0.0, 0.0, -0.25},
    {-0.25, 0.25, 0.0, 0.0, 0.0, 0.25},  {-0.25, -0.25, 0.0, 0.0, 0.0, -0.25},

    {0.0, 0.0, 0.25, -0.25, 0.25, 0.0},  {0.0, 0.0, 0.25, 0.25, 0.25, 0.0},
    {0.0, 0.0, 0.25, -0.25, -0.25, 0.0}, {0.0, 0.0, 0.25, 0.25, -0.25, 0.0}};

void normalize_thrusters(float output[8]);

void multiply_matrix(float V[6]) {
  for (int i = 0; i < 8; i++) {
    output[i] = 0.0f;
    for (int j = 0; j < 6; j++) {
      output[i] += A_inv[i][j] * V[j];
    }
  }
  normalize_thrusters(output);
}

void normalize_thrusters(float output[8]) {
  float maxH = 0.0f;
  float maxV = 0.0f;
  for (int i = 0; i < 4; i++) {
    float val = fabs(output[i]);
    if (val > maxH) {
      maxH = val;
    }
  }
  if (maxH > 1.0f) {

    for (int i = 0; i < 4; i++) {
      output[i] /= maxH;
    }
  }

  for (int i = 4; i < 8; i++) {
    float val = fabs(output[i]);
    if (val > maxV) {
      maxV = val;
    }
  }
  if (maxV > 1.0f) {

    for (int i = 4; i < 8; i++) {
      output[i] /= maxV;
    }
  }
}

struct Controller {
  explicit constexpr Controller(const PID &angle_pid,
                                const std::optional<PID> &rate_pid)
      : angle_pid(angle_pid), rate_pid(rate_pid) {}

private:
  PID angle_pid;
  std::optional<PID> rate_pid = std::nullopt;

public:
  float output(float setpoint, float angle,
               std::optional<float> rate = std::nullopt) {}
};

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

  uint32_t last_send_time = 0;
  while (1) {
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
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
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
void assert_failed(uint8_t *file, uint32_t line) {
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line
     number, ex: printf("Wrong parameters value: file %s on line %d\r\n", file,
     line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
