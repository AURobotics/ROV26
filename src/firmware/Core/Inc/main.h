/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "../../USB_DEVICE/App/usb_comms.h"
/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define LIMIT_SWITCH_CLOSED_Pin GPIO_PIN_14
#define LIMIT_SWITCH_CLOSED_GPIO_Port GPIOC
#define LIMIT_SWITCH_OPEN_Pin GPIO_PIN_15
#define LIMIT_SWITCH_OPEN_GPIO_Port GPIOC
#define LEAKAGE_SENSOR_2_Pin GPIO_PIN_0
#define LEAKAGE_SENSOR_2_GPIO_Port GPIOA
#define MOTOR_5_B_Pin GPIO_PIN_1
#define MOTOR_5_B_GPIO_Port GPIOA
#define MOTOR_5_A_Pin GPIO_PIN_2
#define MOTOR_5_A_GPIO_Port GPIOA
#define MOTOR_8_A_Pin GPIO_PIN_3
#define MOTOR_8_A_GPIO_Port GPIOA
#define LEAKAGE_SENSOR_1_Pin GPIO_PIN_4
#define LEAKAGE_SENSOR_1_GPIO_Port GPIOA
#define MOTOR_4_B_Pin GPIO_PIN_5
#define MOTOR_4_B_GPIO_Port GPIOA
#define MOTOR_4_A_Pin GPIO_PIN_6
#define MOTOR_4_A_GPIO_Port GPIOA
#define MOTOR_3_B_Pin GPIO_PIN_7
#define MOTOR_3_B_GPIO_Port GPIOA
#define MOTOR_3_A_Pin GPIO_PIN_0
#define MOTOR_3_A_GPIO_Port GPIOB
#define MOTOR_2_A_Pin GPIO_PIN_1
#define MOTOR_2_A_GPIO_Port GPIOB
#define LED_FLASHER_Pin GPIO_PIN_2
#define LED_FLASHER_GPIO_Port GPIOB
#define MOTOR_2_B_Pin GPIO_PIN_10
#define MOTOR_2_B_GPIO_Port GPIOB
#define MOTOR_GRIPPER_A_Pin GPIO_PIN_12
#define MOTOR_GRIPPER_A_GPIO_Port GPIOB
#define MOTOR_GRIPPER_B_Pin GPIO_PIN_13
#define MOTOR_GRIPPER_B_GPIO_Port GPIOB
#define DCV_1_Pin GPIO_PIN_14
#define DCV_1_GPIO_Port GPIOB
#define DCV_2_Pin GPIO_PIN_15
#define DCV_2_GPIO_Port GPIOB
#define I2C_SCL_Pin GPIO_PIN_8
#define I2C_SCL_GPIO_Port GPIOA
#define MOTOR_1_A_Pin GPIO_PIN_9
#define MOTOR_1_A_GPIO_Port GPIOA
#define MOTOR_1_B_Pin GPIO_PIN_10
#define MOTOR_1_B_GPIO_Port GPIOA
#define MOTOR_8_B_Pin GPIO_PIN_3
#define MOTOR_8_B_GPIO_Port GPIOB
#define I2C_SDA_Pin GPIO_PIN_4
#define I2C_SDA_GPIO_Port GPIOB
#define POWER_RELAY_Pin GPIO_PIN_5
#define POWER_RELAY_GPIO_Port GPIOB
#define MOTOR_7_A_Pin GPIO_PIN_6
#define MOTOR_7_A_GPIO_Port GPIOB
#define MOTOR_7_B_Pin GPIO_PIN_7
#define MOTOR_7_B_GPIO_Port GPIOB
#define MOTOR_6_B_Pin GPIO_PIN_8
#define MOTOR_6_B_GPIO_Port GPIOB
#define MOTOR_6_A_Pin GPIO_PIN_9
#define MOTOR_6_A_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
