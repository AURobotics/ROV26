#ifndef ESP_MQTT_CLIENT_H
#define ESP_MQTT_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

class ESPMQTTClient
{
public:
    // Constructor
    ESPMQTTClient(
        const char *ssid,
        const char *password = "12345678",
        const char *mqtt_server = "localhost",
        int mqtt_port = 1883,
        const char *mqtt_user = nullptr,
        const char *mqtt_password = nullptr,
        const char *client_id = nullptr);

    // Destructor
    ~ESPMQTTClient();

    // Public methods
    void begin();
    void loop();
    bool publish(const char *topic, const char *payload, bool retained = false);
    bool subscribe(const char *topic);
    bool unsubscribe(const char *topic);
    bool isConnected();
    void disconnect();
    void setCallback(std::function<void(char *, uint8_t *, unsigned int)> callback);

    // Configuration methods
    void setWill(const char *topic, const char *message, bool retained = false);
    void setKeepAlive(uint16_t keepAlive);
    void setCleanSession(bool clean);

private:
    // WiFi credentials
    const char *_ssid;
    const char *_password;

    // MQTT broker settings
    const char *_mqtt_server;
    int _mqtt_port;
    const char *_mqtt_user;
    const char *_mqtt_password;
    char *_generatedID;
    const char *_client_id;

    // MQTT options
    uint16_t _keepAlive = 15;
    bool _cleanSession = true;
    const char *_willTopic = nullptr;
    const char *_willMessage = nullptr;
    bool _willRetained = false;

    // WiFi and MQTT clients
    WiFiClient _wifiClient;
    PubSubClient _mqttClient;

    // Callback function
    std::function<void(char *, uint8_t *, unsigned int)> _callback;

    // Private methods
    void connectToWiFi();
    void connectToMQTT();
    void generateClientID();
    static void mqttCallback(char *topic, byte *payload, unsigned int length);
};

#endif