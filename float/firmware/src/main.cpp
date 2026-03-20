#include <Arduino.h>
#include <ESPMQTTClient.h>
#include "ota_manager.h"
#include <WiFi.h>
#include "store_data.h"
#include "mqtt_manager.h"

// WiFi credentials
const char *WIFI_SSID = "";
const char *WIFI_PASSWORD = "";

// MQTT broker settings
const char *MQTT_BROKER = "192.168.1.9";
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optional

// network settings
const bool AS_ACCESS_POINT = false;

void connectToWiFi(const char *ssid, const char *password, bool asAccessPoint);
void initAccessPoint(const char *ssid, const char *password);

MQTTManager mqttManager;

// depths values for testing
float testDepth = 0.0;
float depthIncrement = 0.1;

void setup()
{
    Serial.begin(115200);
    connectToWiFi(WIFI_SSID, WIFI_PASSWORD, AS_ACCESS_POINT);

    // OTA
    // setupOTA();

    // MQTT setup
    mqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);

    store_data_setup();
}

void loop()
{
    // Handle OTA updates
    // otaupdate();

    // Handle MQTT communication
    mqttManager.loop();

    // To store depth per time
    store_data_loop();

    if (isComplete())
    {
        Serial.println("sending data to mqtt");

        // Ensure WiFi is still connected before checking MQTT state
        if (WiFi.status() != WL_CONNECTED)
        {
            Serial.println("WiFi connection lost. Reconnecting...");
            WiFi.reconnect();
            delay(500);
        }

        mqttManager.sendFileChunked("float/data", "/data.csv");
    }

    // For testing without sensor, simulating depth changes
    testDepth += depthIncrement;
}

void connectToWiFi(const char *ssid, const char *password, bool asAccessPoint)
{
    if (asAccessPoint)
    {
        initAccessPoint(ssid, password);
    }
    else
    {
        Serial.print("Connecting to WiFi");
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid, password);

        // Poll every 500ms until connected
        while (WiFi.status() != WL_CONNECTED)
        {
            delay(500);
            Serial.print("Connecting to WiFi..");
        }

        Serial.println("\nWiFi connected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
    }
}

// If needed to set up as access point instead of connecting to existing WiFi network
void initAccessPoint(const char *ssid, const char *password)
{
    IPAddress local_IP(192, 168, 1, 22);
    IPAddress gateway(192, 168, 1, 5);
    IPAddress subnet(255, 255, 255, 0);

    Serial.print("Setting up Access Point ... ");
    Serial.println(WiFi.softAPConfig(local_IP, gateway, subnet) ? "Ready" : "Failed!");

    Serial.print("Starting Access Point ... ");
    Serial.println(WiFi.softAP(ssid, password) ? "Ready" : "Failed!");

    Serial.print("IP address = ");
    Serial.println(WiFi.softAPIP());
}