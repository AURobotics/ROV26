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
bool MqttSetupDone = false;

// pressure sensor
MS5611 pressureSensor = MS5611();
float depth = 0.0f;

void setup()
{
    Serial.begin(115200);

    // OTA
    // setupOTA();

    store_data_setup();

    // setup and calibrate pressure sensor
    if (!pressureSensor.begin())
    {
        Serial.println("Failed to initialize MS5611 sensor!");
        delay(1000);
        ESP.restart();
    }
}

void loop()
{
    // Handle OTA updates
    // otaupdate();

    // To store depth per time
    store_data_loop();

    if (isComplete())
    {
        // MQTT setup
        Serial.println("Connecting to MQTT broker...");

        if (!MqttSetupDone)
        {
            connectToNetwork();
            MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
            MqttSetupDone = true;
        }

        // keep sending data to MQTT broker every 5 seconds till shutdown
        while (1)
        {
            // Handle MQTT communication
            MqttManager.loop();

            Serial.println("sending data to mqtt");

            // Ensure WiFi is still connected before checking MQTT state
            if (WiFi.status() != WL_CONNECTED)
            {
                Serial.println("WiFi connection lost. Reconnecting...");
                WiFi.reconnect();
                delay(500);
            }
            Serial.print("Mqtt connection is: ");
            Serial.println(MqttManager.isConnected() ? "Connected" : "Not Connected");

            MqttManager.publishFileChunkedOverTopics("float/data", "/littlefs/log.csv", "log.csv");
            delay(5000); // Send data every 5 seconds
        }
    }

    // depth = testDepth;
    depth = pressureSensor.getDepth();
    setDepth(depth);

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

/*
Mqtt connection is: Connected
E (60226) mqtt_client: esp_mqtt_handle_transport_read_error: transport_read(): EOF
E (60226) mqtt_client: esp_mqtt_handle_transport_read_error: transport_read() error: errno=128
E (60231) IDFMQTTClient: MQTT_EVENT_ERROR
E (60234) IDFMQTTClient:   esp_tls_last_esp_err  = 0x8008
E (60239) IDFMQTTClient:   esp_tls_stack_err     = 0x0
E (60244) IDFMQTTClient:   esp_transport_sock_errno = 0
E (60249) mqtt_client: mqtt_process_receive: mqtt_message_receive() returned -2
E (60258) IDFMQTTClient: Lost connection at chunk 0/7
Attempt 1/3 failed, retrying...
E (75801) mqtt_client: esp_mqtt_handle_transport_read_error: transport_read(): EOF
E (75802) mqtt_client: esp_mqtt_handle_transport_read_error: transport_read() error: errno=128
E (75806) IDFMQTTClient: MQTT_EVENT_ERROR
E (75810) IDFMQTTClient:   esp_tls_last_esp_err  = 0x8008
E (75815) IDFMQTTClient:   esp_tls_stack_err     = 0x0
E (75820) IDFMQTTClient:   esp_transport_sock_errno = 0
E (75825) mqtt_client: mqtt_process_receive: mqtt_message_receive() returned -2
E (75833) IDFMQTTClient: Lost connection at chunk 0/7
Attempt 2/3 failed, retrying...
*/