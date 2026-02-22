#include <ESPMQTTClient.h>

#define LED_BUILTIN 0

// WiFi credentials
const char *WIFI_SSID = "your_wifi_ssid";
const char *WIFI_PASSWORD = "your_wifi_password";

// MQTT broker settings
const char *MQTT_SERVER = "broker.emqx.io"; // Public test broker
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optional

// Create MQTT client instance
ESPMQTTClient mqttClient(
    WIFI_SSID,
    WIFI_PASSWORD,
    MQTT_SERVER,
    MQTT_PORT,
    MQTT_USER,
    MQTT_PASSWORD);

void setup()
{
    Serial.begin(115200);

    // Set Last Will and Testament (optional)
    mqttClient.setWill("esp/status", "disconnected", true);

    // Set callback for incoming messages
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
        Serial.println(message);
        
        // Example: Turn on/off LED based on message
        if (strcmp(topic, "esp/led") == 0) {
            if (strcmp(message, "ON") == 0) {
                digitalWrite(LED_BUILTIN, LOW);  // Turn on LED
                mqttClient.publish("esp/led/status", "ON");
            } else if (strcmp(message, "OFF") == 0) {
                digitalWrite(LED_BUILTIN, HIGH); // Turn off LED
                mqttClient.publish("esp/led/status", "OFF");
            }
        } });

    // Initialize the client
    mqttClient.begin();

    // Subscribe to topics
    mqttClient.subscribe("esp/led");
    mqttClient.subscribe("esp/#");

    // Publish connection status
    mqttClient.publish("esp/status", "connected", true);
    mqttClient.publish("esp/ip", WiFi.localIP().toString().c_str(), true);

    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, HIGH); // Start with LED off
}

void loop()
{
    mqttClient.loop();

    // Publish sensor data every 10 seconds
    static unsigned long lastPublish = 0;
    if (millis() - lastPublish > 10000)
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

        if (mqttClient.publish("esp/sensors", payload))
        {
            Serial.println("Sensor data published");
        }
    }
}