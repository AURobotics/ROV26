#include "mqtt_manager.h"
#include <ESPMqttClient.h>

char *startingIP = "192.168.4.2"; // in case of access point mode, this will be the starting IP of the AP
char *IP2 = "192.168.4.3";
char *IP3 = "192.168.4.4";
char *IP4 = "192.168.4.5";
char *IP5 = "192.168.4.6";

char *IPs[] = {startingIP, IP2, IP3, IP4, IP5};

MQTTManager::MQTTManager() : _mqttClient(nullptr) {}

void MQTTManager::setup(const char *mqtt_broker, int mqtt_port,
                        const char *mqtt_username, const char *mqtt_password, bool asAccessPoint)
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
    bool res = _mqttClient->begin();

    if (!res && asAccessPoint)
    {
        Serial.println("Running in Access Point mode. Connect to the AP and use the following IPs:");
        for (const char *ip : IPs)
        {
            if (!res)
            {
                delete _mqttClient;
                _mqttClient = new ESPMqttClient(ip, mqtt_port, mqtt_username, mqtt_password);
                _mqttClient->setCallback(messageCallback);
                res = _mqttClient->begin();
            }
        }
    }
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

bool MQTTManager::sendFileChunkedOverTopics(const char *topic, const char *filename)
{
    if (_mqttClient != nullptr)
    {
        return _mqttClient->sendFileChunkedOverTopics(topic, filename);
    }
    return false;
}

bool MQTTManager::sendFileChunkedWithFeedback(const char *topic, const char *filename)
{
    if (_mqttClient != nullptr)
    {
        return _mqttClient->sendFileChunkedWithFeedback(topic, filename);
    }
    return false;
}