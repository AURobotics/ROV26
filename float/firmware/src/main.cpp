#include <Arduino.h>
#include <ESPMQTTClient.h>
#include "ota_manager.h"
#include <WiFi.h>
#include "store_data.h"

void connectToWiFi(const char *ssid, const char *password, bool asAccessPoint);
void initAccessPoint(const char *ssid, const char *password);
void setMqttCallback();

// WiFi credentials
const char *WIFI_SSID = "";
const char *WIFI_PASSWORD = "";

// MQTT broker settings
const char *MQTT_SERVER = "192.168.1.9";
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optional
const bool AS_ACCESS_POINT = false;
// Create MQTT client instance
ESPMqttClient mqttClient(
    MQTT_SERVER,
    MQTT_PORT,
    MQTT_USER,
    MQTT_PASSWORD);

// ArduinoOTAClass ArduinoOTA;

void setup()
{
    Serial.begin(115200);
    connectToWiFi(WIFI_SSID, WIFI_PASSWORD, AS_ACCESS_POINT);

    // OTA
    // setupOTA();

    // Set callback for incoming messages
    setMqttCallback();

    // Initialize the client
    mqttClient.begin();

    // Subscribe to topics
    mqttClient.subscribe("to/esp");

    store_data_setup();
}

void loop()
{
    // Handle OTA updates
    // otaupdate();

    // Handle MQTT communication
    mqttClient.loop();

    // To store depth per time
    store_data_loop();

    // Ensure WiFi is still connected before checking MQTT state
    if (WiFi.status() != WL_CONNECTED)
    {
        Serial.println("WiFi connection lost. Reconnecting...");
        WiFi.reconnect();
        delay(500);
    }

    // TEST: Publish sensor data every 5 seconds
    static unsigned long lastPublish = 0;
    if (millis() - lastPublish > 5000)
    {
        lastPublish = millis();

        // Simulate sensor reading
        float temperature = random(200, 300) / 10.0; // 20.0 - 30.0 °C
        float humidity = random(400, 800) / 10.0;    // 40.0 - 80.0 %

        // Create JSON payload
        char payload[100];
        snprintf(payload, sizeof(payload),
                 "{\"temperature\":%.1f,\"humidity\":%.1f}",
                 temperature, humidity);

        if (mqttClient.publish("from/esp", payload))
        {
            Serial.println("Sensor data published: " + String(payload));
        }
    }
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

void setMqttCallback()
{
    mqttClient.setCallback([](char *topic, uint8_t *payload, unsigned int length)
                           {
        Serial.print("Message arrived [");
        Serial.print(topic);
        Serial.print("] ");
        
        char message[length + 1];
        for (unsigned int i = 0; i < length; i++) {
            message[i] = (char)payload[i];
        }
        message[length] = '\0';
        Serial.println(message); });
}