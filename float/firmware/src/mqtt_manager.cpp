#include "mqtt_manager.h"
#include <ESPMqttClient.h>

MQTTManager::MQTTManager() : _mqttClient(nullptr) {}

void MQTTManager::setup(const char *mqtt_broker, int mqtt_port,
                        const char *mqtt_username, const char *mqtt_password)
{
    // Delete old client if exists
    if (_mqttClient != nullptr)
    {
        delete _mqttClient;
    }

    // Create new client
    _mqttClient = new ESPMqttClient(mqtt_broker, mqtt_port, mqtt_username, mqtt_password);

    // Set callback
    _mqttClient->setCallback(messageCallback);

    // Initialize
    _mqttClient->begin();
    _mqttClient->subscribe("to/esp");
}

void MQTTManager::loop(bool pollMqttConnection)
{
    if (_mqttClient != nullptr)
    {
        _mqttClient->loop(pollMqttConnection);
    }
}

bool MQTTManager::publish(const char *topic, const char *payload, bool retained)
{
    if (_mqttClient != nullptr)
    {
        return _mqttClient->publish(topic, payload, retained);
    }
    return false;
}

void MQTTManager::messageCallback(char *topic, uint8_t *payload, unsigned int length)
{
    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("] ");

    char message[length + 1];
    for (unsigned int i = 0; i < length; i++)
    {
        message[i] = (char)payload[i];
    }
    message[length] = '\0';
    Serial.println(message);
}

bool MQTTManager::sendFileChunked(const char *topic, const char *filename)
{
    if (_mqttClient != nullptr)
    {
        return _mqttClient->sendFileChunked(topic, filename);
    }
    return false;
}