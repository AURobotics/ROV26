#include "main.h"
#include "PID.h"
#include "adc.h"
#include "gpio.h"
#include "i2c.h"
#include "tim.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"

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
 // water leakage
 #define LEAKAGE_THRESHOLD  2000U //need to be adjusted based on testing
static uint32_t read_adc(uint32_t channel) {
  ADC_ChannelConfTypeDef sConfig = {};
  sConfig.Channel = channel;
  sConfig.Rank = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_84CYCLES; //sampling time is 84 cycles, which is 84/84MHz = 1us
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK) return 0u; 

  HAL_ADC_Start(&hadc1);
  if (HAL_ADC_PollForConversion(&hadc1,10)!= HAL_OK) return 0u; 
  uint32_t value = HAL_ADC_GetValue(&hadc1);
  HAL_ADC_Stop(&hadc1);
  return value;
}


volatile bool leakage_safety_enabled = true;
volatile bool leak_detected = false;  // Latched leak flag --> once a leak is detected the relay stays off 
static void checkWaterLeakage() {
  if (!leakage_safety_enabled) {
    // Safety disabled, ensure relay is energised
    HAL_GPIO_WritePin(POWER_RELAY_GPIO_Port, POWER_RELAY_Pin, GPIO_PIN_SET); 
    return; 
  }
 
 if (leak_detected) {
    // Leak already detected, ensure relay is tripped
    HAL_GPIO_WritePin(POWER_RELAY_GPIO_Port, POWER_RELAY_Pin, GPIO_PIN_RESET);
    return;
  }

  uint32_t sensor1 = read_adc(LEAKAGE_ADC_CHANNEL_1);
  uint32_t sensor2 = read_adc(LEAKAGE_ADC_CHANNEL_2);

    if (sensor1 > LEAKAGE_THRESHOLD || sensor2 > LEAKAGE_THRESHOLD) {
        leak_detected = true;
        // Leak detected --> trip the relay
        HAL_GPIO_WritePin(POWER_RELAY_GPIO_Port, POWER_RELAY_Pin, GPIO_PIN_RESET);
    } else {
        // No leak detected --> ensure relay is energized if not already tripped
        HAL_GPIO_WritePin(POWER_RELAY_GPIO_Port, POWER_RELAY_Pin, GPIO_PIN_SET);
    }
}


void leakageCommsHandler(uint8_t cmd) {
    switch (cmd) {
        case COMS_LEAKAGE_SAFETY_ENABLE:
            leakage_safety_enabled = true;
            leak_detected = false; 
            HAL_GPIO_WritePin(POWER_RELAY_GPIO_Port, POWER_RELAY_Pin, GPIO_PIN_SET); 
            break;
        case COMS_LEAKAGE_SAFETY_DISABLE:
            leakage_safety_enabled = false;
            leak_detected = false;
              HAL_GPIO_WritePin(POWER_RELAY_GPIO_Port, POWER_RELAY_Pin, GPIO_PIN_SET);  
            break;
        default:
            break;
    }
}
// End of water leakage code

//gripper limit switch
volatile bool gripper_safety_enabled = true;
static void GripperStop(void){
  HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_RESET);
}
static void GripperOpen(void){
  HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_SET);
  HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_RESET);
}
static void GripperClose(void){
  HAL_GPIO_WritePin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin, GPIO_PIN_SET);
}
static void checkGripperLimitSwitches() {
  if (!gripper_safety_enabled) {
    return; 
  }
  GPIO_PinState openState = HAL_GPIO_ReadPin(LIMIT_SWITCH_OPEN_GPIO_Port, LIMIT_SWITCH_OPEN_Pin);
  GPIO_PinState closedState = HAL_GPIO_ReadPin(LIMIT_SWITCH_CLOSED_GPIO_Port, LIMIT_SWITCH_CLOSED_Pin);

  GPIO_PinState gripperAState = HAL_GPIO_ReadPin(MOTOR_GRIPPER_A_GPIO_Port, MOTOR_GRIPPER_A_Pin);
  GPIO_PinState gripperBState = HAL_GPIO_ReadPin(MOTOR_GRIPPER_B_GPIO_Port, MOTOR_GRIPPER_B_Pin);

  bool isOpening = (gripperAState == GPIO_PIN_SET && gripperBState == GPIO_PIN_RESET);
  bool isClosing = (gripperAState == GPIO_PIN_RESET && gripperBState == GPIO_PIN_SET);

  if (isOpening && openState == GPIO_PIN_SET) {
    GripperStop();
  } else if (isClosing && closedState == GPIO_PIN_SET) {
    GripperStop();
  }
}


void gripperCommsHandler(uint8_t cmd) {
  GPIO_PinState openState = HAL_GPIO_ReadPin(LIMIT_SWITCH_OPEN_GPIO_Port, LIMIT_SWITCH_OPEN_Pin);
  GPIO_PinState closedState = HAL_GPIO_ReadPin(LIMIT_SWITCH_CLOSED_GPIO_Port, LIMIT_SWITCH_CLOSED_Pin);
    switch (cmd) {
        case COMS_GRIPPER_OPEN:
            if (gripper_safety_enabled&&openState == GPIO_PIN_SET) { // Only open if not already at open limit
                GripperStop();
            }
            else {
                GripperOpen();
            }
            break;
        case COMS_GRIPPER_CLOSE:
            if (gripper_safety_enabled&&closedState == GPIO_PIN_SET) {  // Only close if not already at closed limit
                GripperStop();
            }
            else {
                GripperClose();
            }
            break;
        case COMS_GRIPPER_STOP:
            GripperStop();
            break;
        case COMS_GRIPPER_SAFETY_ENABLE:
            gripper_safety_enabled = true;
            break;
        case COMS_GRIPPER_SAFETY_DISABLE:
            gripper_safety_enabled = false;
              break;
        default:
            break;
    }
}
static void sendGripperStatus() {
  GPIO_PinState openState = HAL_GPIO_ReadPin(LIMIT_SWITCH_OPEN_GPIO_Port, LIMIT_SWITCH_OPEN_Pin);
  GPIO_PinState closedState = HAL_GPIO_ReadPin(LIMIT_SWITCH_CLOSED_GPIO_Port, LIMIT_SWITCH_CLOSED_Pin);

  uint8_t statusByte = 0x00;
  if (openState == GPIO_PIN_SET) {
    statusByte |= (1<<1); // bit 1 indicates open limit reached
  }
  if (closedState == GPIO_PIN_SET) {
    statusByte |= (1<<0); // bit 0 indicates closed limit reached
  }
  uint8_t packet[3] = {GRIPPER_TELEMETRY_ID, statusByte, 0x00}; 
  CDC_Transmit_FS(packet, sizeof(packet)); // Transmit the status packet over USB CDC
  
}
// End of gripper limit switch 

//communication loss 
#define TIMEOUT_MS   500U   // ms of silence before declaring comms lost
#define BLINK_MS     100U  // ms for toggling LED to indicate comms loss
  volatile uint32_t lastCommsTime = 0;

 static void StopMotors(void){
  GripperStop();
  HAL_GPIO_WritePin(MOTOR_1_A_GPIO_Port, MOTOR_1_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_1_B_GPIO_Port, MOTOR_1_B_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_2_A_GPIO_Port, MOTOR_2_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_2_B_GPIO_Port, MOTOR_2_B_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_3_A_GPIO_Port, MOTOR_3_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_3_B_GPIO_Port, MOTOR_3_B_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_4_A_GPIO_Port, MOTOR_4_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_4_B_GPIO_Port, MOTOR_4_B_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_5_A_GPIO_Port, MOTOR_5_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_5_B_GPIO_Port, MOTOR_5_B_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_6_A_GPIO_Port, MOTOR_6_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_6_B_GPIO_Port, MOTOR_6_B_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_7_A_GPIO_Port, MOTOR_7_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_7_B_GPIO_Port, MOTOR_7_B_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_8_A_GPIO_Port, MOTOR_8_A_Pin, GPIO_PIN_RESET);
  HAL_GPIO_WritePin(MOTOR_8_B_GPIO_Port, MOTOR_8_B_Pin, GPIO_PIN_RESET);
 }

  static void checkCommsTimeout() {
    static bool     CommsLostPrev   = false; // tracks previous state for edge detection
  static uint32_t BlinkTick        = 0;     // last LED toggle time
  static bool     LedState         = false;
    uint32_t now = HAL_GetTick();
    bool commsLost = (now - lastCommsTime > TIMEOUT_MS);
    if (commsLost) {
      if (!CommsLostPrev) {
      // Comms timeout --> stop all motors and indicate loss of comms
      StopMotors();
    }
  if ((now - BlinkTick) >= BLINK_MS) {
    LedState = !LedState;
    HAL_GPIO_WritePin(LED_FLASHER_GPIO_Port, LED_FLASHER_Pin, LedState ? GPIO_PIN_SET : GPIO_PIN_RESET);
    BlinkTick = now;
  }}
else{
  LedState = false;
  HAL_GPIO_WritePin(LED_FLASHER_GPIO_Port,LED_FLASHER_Pin, GPIO_PIN_RESET);
}
  CommsLostPrev = commsLost;
    }

    // End of communication loss
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

  HAL_GPIO_WritePin(POWER_RELAY_GPIO_Port, POWER_RELAY_Pin, GPIO_PIN_SET); // power relay on by default
  GripperStop(); // ensure gripper is stopped by default
  lastCommsTime = HAL_GetTick(); // initialize comms timer
  uint32_t lastTelemetrySend = 0;
  while (1) {
    checkCommsTimeout();
    checkWaterLeakage();
    checkGripperLimitSwitches();
    uint32_t now = HAL_GetTick();
    if (now - lastTelemetrySend >= 20u) { // Send gripper status every 20ms
      sendGripperStatus();
      lastTelemetrySend = now;
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
