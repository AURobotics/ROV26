#include <Arduino.h>
#include <ArduinoMQTTClient.h>
#include <IDFMQTTClient.h>
#include "ota_manager.h"
#include <WiFi.h>
#include "store_data.h"
#include "arduino_mqtt_manager.h"
#include "idf_mqtt_manager.h"
#include <ms5611.h>

// WiFi credentials
const char *WIFI_SSID = "";
const char *WIFI_PASSWORD = "";

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

// ArduinoMqttManager MqttManager;
IDFMQTTManager MqttManager;

// depths values for testing
// float testDepth = 0.0;
// float depthIncrement = 0.1;

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
    // setupOTA();

    // @attention - Logic to change state is not implemented yet
    while (currentState == IDLE)
    {
        // Wait for sequence to complete
        delay(50);
    }

    // setup and calibrate pressure sensor
    if (!pressureSensor.begin())
    {
        Serial.println("Failed to initialize MS5611 sensor!");
        delay(1000);
        ESP.restart();
    }

    // Start the sequence
    if (!store_data_setup())
    {
        Serial.println("Failed to setup data storage!");
        delay(1000);
        ESP.restart();
    }
}

void loop()
{
    // Handle OTA updates
    // otaupdate();

    if (currentState == COLLECTING)
    {
        // To store depth per time
        store_data_loop();

        // depth = testDepth;
        depth = pressureSensor.getDepth();
        setDepth(depth);

        if (isComplete())
        {
            currentState = UPLOADING;
        }

        // // For testing depth changes without sensor
        // if (abs(depth - getCurrentTarget()) < 0.05)
        // {
        //     Serial.println("At target depth, holding...");
        //     setDepth(depth);
        //     delay(500); // Wait for 30 seconds
        //     setDepth(depth);
        //     delay(500);
        //     setDepth(depth);
        // }
        // else if (depth > getCurrentTarget())
        // {
        //     depth -= depthIncrement; // Move slightly below target
        // }
        // else
        // {
        //     depth += depthIncrement;
        // }
        // setDepth(depth);

        Serial.print("Current Target: ");
        Serial.println(getCurrentTarget());
        Serial.print("Current Depth: ");
        Serial.println(depth);

        // delay(500);
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
            delay(500);

            if (WiFi.status() == WL_CONNECTED)
            {
                MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
                wifiRetryCount = 0; // reset retry count on successful reconnection
                wifiState = true;
            }
            else if (wifiRetryCount >= MAX_WIFI_RETRY_COUNT)
            {
                Serial.println("Failed to reconnect after multiple attempts. Restarting network...");
                delay(5000);
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

            Serial.println("sending data to mqtt");

            Serial.print("Mqtt connection is: ");
            Serial.println(MqttManager.isConnected() ? "Connected" : "Not Connected");

            MqttManager.publishFileChunkedOverTopics("float/data", "/littlefs/log.csv", "log.csv");
            delay(5000); // Send data every 5 seconds
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
            delay(500);
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
        delay(1000);
        WiFi.mode(WIFI_OFF);
        delay(500);
        WiFi.mode(WIFI_STA);
        delay(500);
        WiFi.begin(ssid, password); // restart for next retry
    }

    Serial.println("\nWiFi connection failed after all retries!");
    return false;
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
            delay(1000);
        }
    }

    Serial.println("ERROR: Could not start Access Point!");
    return false;
}
