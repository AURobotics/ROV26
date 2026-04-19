#ifndef MISCELLANEOUS_H
#define MISCELLANEOUS_H

#include <Arduino.h>
#include <IDFMQTTClient.h>
#include "ota_manager.h"
#include <WiFi.h>
#include "store_data.h"
#include "idf_mqtt_manager.h"
#include <ms5611.h>
#include <Wire.h>

#define BLINKING_LED 2 // to make sure esp is ok :|

#define COMPANY_NUMBER "AU Robotics"

// WiFi credentials
const char *WIFI_SSID = "Abdelaziz";
const char *WIFI_PASSWORD = "ya moshel";

// MQTT broker settings
const char *MQTT_BROKER = "10.14.70.135";
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optional

// network settings
bool AS_ACCESS_POINT = false;

bool connectToNetwork(bool asAccessPoint = false);
bool connectToWiFi(const char *ssid, const char *password, int maxRetries = 0);
bool initAccessPoint(const char *ssid, const char *password, int maxRetries = 0);
void myDelay(unsigned long ms, bool resetOtaWatchdog = true);
void setMessageOnCallBack();

// ArduinoMqttManager MqttManager;
IDFMQTTManager MqttManager;

// pressure sensor
MS5611 pressureSensor = MS5611();
float depth = 0.0f;

enum Led
{
    RUNNING = 19,   // red
    UPLOADING = 5,  // blue // Collecting data and doing operations
    CONNECTION = 18 // green // Uploading data to MQTT broker
};
Led currentState;
constexpr int POWER = 23; // pin set high to retain power, set low to shut down

#define MAX_WIFI_RETRY_COUNT 5

// // timer to trigger if otaupdate stopped from being called
// hw_timer_t *otaWatchdogTimer = NULL;
// const int timeout_ms = 3000; // 1 seconds

// void callOtaupdate()
// {
//     // To reset: Restart the timer from 0
//     timerRestart(otaWatchdogTimer);

//     // Ensure the alarm is still active
//     timerWrite(otaWatchdogTimer, 0);

//     otaupdate();
// }

// // This function runs if the timer expires
// void IRAM_ATTR onTimer()
// {
//     digitalWrite(POWER, HIGH);
//     ESP.restart();
// }

void initPins()
{
    pinMode(RUNNING, OUTPUT);
    pinMode(UPLOADING, OUTPUT);
    pinMode(CONNECTION, OUTPUT);
    pinMode(POWER, OUTPUT);
    pinMode(BLINKING_LED, OUTPUT);
}

#endif