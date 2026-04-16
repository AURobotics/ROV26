#include <Arduino.h>
#include <ArduinoMQTTClient.h>
#include <IDFMQTTClient.h>
#include "ota_manager.h"
#include <WiFi.h>
#include "store_data.h"
#include "arduino_mqtt_manager.h"
#include "idf_mqtt_manager.h"
#include <ms5611.h>

#define COMPANY_NUMBER "AU Robotics"
//test OTA
//const int ledPin = 2;

// WiFi credentials
const char *WIFI_SSID = "realme 12";
const char *WIFI_PASSWORD = "12345678";

// MQTT broker settings
const char *MQTT_BROKER = "192.168.1.9";
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optional

// network settings
bool AS_ACCESS_POINT = false;

void connectToNetwork();
bool connectToWiFi(const char *ssid, const char *password);
bool initAccessPoint(const char *ssid, const char *password);
void myDelay(unsigned long);

// ArduinoMqttManager MqttManager;
IDFMQTTManager MqttManager;

// depths values for testing ######################################
float depthIncrement = 0.1;

// Flag to ensure MQTT setup is done only once
bool wifiState = false;

// pressure sensor
MS5611 pressureSensor = MS5611();
float depth = 0.0f;

enum State
{
    IDLE,
    COLLECTING, // Collecting data and doing operations
    UPLOADING   // Uploading data to MQTT broker
};
State currentState = IDLE;

#define MAX_WIFI_RETRY_COUNT 5
int wifiRetryCount = 0;

void setup()
{
    Serial.begin(115200);

    // OTA
    setupOTA(WIFI_SSID, WIFI_PASSWORD);
    Serial.println("\nConnected! IP address: " + WiFi.localIP().toString());
    Serial.println("OTA Ready");
    //TEST OTA
    //pinMode(ledPin, OUTPUT);
    // @attention - Logic to change state is not implemented yet
    // COMMENTING OUT WAITING LOGIC FOR TESTING WITHOUT SENSOR ############################
    // while (currentState == IDLE)
    // {
    //     // Wait for sequence to complete
    //     myDelay(50);
    // }

    // setup and calibrate pressure sensor
    // COMMENTING OUT SENSOR LOGIC FOR TESTING WITHOUT SENSOR ############################
    // if (!pressureSensor.begin())
    // {
    //     Serial.println("Failed to initialize MS5611 sensor!");
    //     myDelay(1000);
    //     if(!pressureSensor.begin()) // try again before restarting
    //     {
    //         ESP.restart();
    //     }
    //     else
    //     {
    //         Serial.println("MS5611 sensor initialized successfully on second attempt");
    //     }
    // }

    // Start the sequence
    if (!store_data_setup())
    {
        Serial.println("Failed to setup data storage!");
        myDelay(1000);
        if (!store_data_setup()) // try again before restarting
        {
            ESP.restart();
        }
        else
        {
            Serial.println("Data storage setup successful on second attempt");
        }
    }

    connectToNetwork();
    MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
    MqttManager.loop(); // checks for mqtt connection and reconnects if needed
    Serial.println("sending: \"Device started and about to collect data\"");
    MqttManager.publish("float/status", "Device started and about to collect data");
    Serial.println("sent initial status message to MQTT broker");
    MqttManager.disconnect();
    WiFi.disconnect();

    // for testing without sensor, start sequence immediately
    currentState = COLLECTING; // ###########################################################
}

void loop()
{
    // Handle OTA updates
     otaupdate();
     //TEST OTA
    /* static unsigned long ledTimer = 0;
     if (millis() - ledTimer >= 1000)
     {
         ledTimer = millis();
         digitalWrite(ledPin, !digitalRead(ledPin)); // Toggle LED
     }
    /**************/
     if (currentState == COLLECTING)
     {
         Serial.println("Collecting data...");

         // To store depth per time
         store_data_loop();

         // COMMENTING OUT SENSOR LOGIC FOR TESTING WITHOUT SENSOR ############################
         // depth = pressureSensor.getDepth();
         // setDepth(depth);

         // For testing depth changes without sensor #################################
         if (abs(depth - getCurrentTarget()) < 0.05)
         {
             Serial.println("At target depth, holding...");
             setDepth(depth);
             myDelay(1000); // Wait for 1 second
             setDepth(depth);
             myDelay(1000);
             setDepth(depth);
         }
         else if (depth > getCurrentTarget())
         {
             depth -= depthIncrement; // Move slightly below target
         }
         else
         {
             depth += depthIncrement;
         }
         setDepth(depth);

         Serial.print("Current Target: ");
         Serial.println(getCurrentTarget());
         Serial.print("Current Depth: ");
         Serial.println(depth);

         myDelay(500); // for testing, in real scenario this would be based on sensor reading frequency ############################################

         if (isComplete())
         {
             Serial.println("Data collection complete. Transitioning to UPLOADING state...");
             currentState = UPLOADING;
         }
    }
    else if (currentState == UPLOADING) // keep sending data to MQTT broker every 5 seconds till shutdown
    {
        // MQTT setup
        Serial.println("Connecting to MQTT broker...");

        if (!wifiState)
        {
            connectToNetwork();
            MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
            wifiState = true;
        }

        // Ensure WiFi is still connected before checking MQTT state
        if (WiFi.status() != WL_CONNECTED)
        {
            wifiState = false; // reset MQTT state to trigger reconnection logic
            wifiRetryCount++;
            Serial.println("WiFi connection lost. Reconnecting...");
            WiFi.reconnect();
            myDelay(500);

            if (WiFi.status() == WL_CONNECTED)
            {
                MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
                wifiRetryCount = 0; // reset retry count on successful reconnection
                wifiState = true;
            }
            else if (wifiRetryCount >= MAX_WIFI_RETRY_COUNT)
            {
                Serial.println("Failed to reconnect after multiple attempts. Restarting network...");
                myDelay(5000);
                WiFi.disconnect();
                connectToNetwork();

                if (WiFi.status() == WL_CONNECTED)
                {
                    MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
                    wifiRetryCount = 0; // reset retry count on successful reconnection
                    wifiState = true;
                }
            }
        }

        if (wifiState)
        {
            // Handle MQTT communication
            MqttManager.loop(); // checks for mqtt connection and reconnects if needed

            Serial.println("sending Company Number and file to mqtt");

            Serial.print("Mqtt connection is: ");
            Serial.println(MqttManager.isConnected() ? "Connected" : "Not Connected");

            MqttManager.publish("float/data/credential", COMPANY_NUMBER);
            MqttManager.publishFileChunkedOverTopics("float/data", "/littlefs/log.csv", "log.csv");
            myDelay(5000); // Send data every 5 seconds
        }
    }
}

void connectToNetwork()
{
    if (AS_ACCESS_POINT)
    {
        initAccessPoint(WIFI_SSID, WIFI_PASSWORD);
    }
    else
    {
        if (!connectToWiFi(WIFI_SSID, WIFI_PASSWORD))
        {
            Serial.println("Failed to connect to WiFi -> trying to set up as Access Point");
            AS_ACCESS_POINT = true;
            initAccessPoint(WIFI_SSID, WIFI_PASSWORD);
        }
    }
}

bool connectToWiFi(const char *ssid, const char *password)
{
    Serial.print("Connecting to WiFi");

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    int maxRetries = 3;
    int retryCount = 0;

    while (retryCount < maxRetries)
    {
        int attempts = 0;
        int maxAttempts = 60; // 30 seconds

        while (WiFi.status() != WL_CONNECTED && attempts < maxAttempts)
        {
            myDelay(500);
            Serial.print(".");
            attempts++;
        }

        if (WiFi.status() == WL_CONNECTED)
        {
            Serial.println("\nWiFi connected");
            Serial.print("IP address: ");
            Serial.println(WiFi.localIP());
            return true;
        }

        Serial.println("status: " + String(WiFi.status()));
        retryCount++;
        Serial.printf("\nConnection failed. Retry %d of %d...\n", retryCount, maxRetries);

        WiFi.disconnect();
        myDelay(1000);
        WiFi.mode(WIFI_OFF);
        myDelay(500);
        WiFi.mode(WIFI_STA);
        myDelay(500);
        WiFi.begin(ssid, password); // restart for next retry
    }

    Serial.println("\nWiFi connection failed after all retries!");
    return false;
}

void myDelay(unsigned long ms)
{
    unsigned long start = millis();
    while (millis() - start < ms)
    {
        // Handle OTA updates during delay
         //otaupdate();
        delay(100); // Short delay to prevent watchdog timer reset
    }
}

bool initAccessPoint(const char *ssid, const char *password)
{
    IPAddress local_IP(192, 168, 1, 22);
    IPAddress gateway(192, 168, 1, 5);
    IPAddress subnet(255, 255, 255, 0);

    Serial.print("Setting up Access Point configuration... ");
    if (!WiFi.softAPConfig(local_IP, gateway, subnet))
    {
        Serial.println("FAILED!");
        Serial.println("Using default configuration instead");
        // continue without custom config and use data printed by WiFi.softAPIP() later to know the actual IP address
    }
    else
    {
        Serial.println("OK");
    }

    int maxAttempts = 3; // try multiple times to start AP (sometimes first attempt fails)
    for (int attempt = 1; attempt <= maxAttempts; attempt++)
    {
        Serial.printf("Starting Access Point (attempt %d of %d)... ", attempt, maxAttempts);

        if (WiFi.softAP(ssid, password))
        {
            Serial.println("READY!");
            Serial.print("Access Point IP address: ");
            Serial.println(WiFi.softAPIP());
            Serial.printf("SSID: %s\n", ssid);
            return true;
        }

        Serial.println("FAILED!");
        if (attempt < maxAttempts)
        {
            myDelay(1000);
        }
    }

    Serial.println("ERROR: Could not start Access Point!");
    return false;
}
