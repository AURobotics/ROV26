#include "idf_mqtt_manager.h"
#include <IDFMQTTClient.h>
#include <LittleFS.h>

const char *IDF_startingIP = "192.168.4.2"; // in case of access point mode, this will be the starting IP of the AP
const char *IDF_IP2 = "192.168.4.3";
const char *IDF_IP3 = "192.168.4.4";
const char *IDF_IP4 = "192.168.4.5";
const char *IDF_IP5 = "192.168.4.6";

const char *IDF_IPs[] = {IDF_startingIP, IDF_IP2, IDF_IP3, IDF_IP4, IDF_IP5};

IDFMQTTManager::IDFMQTTManager() : _mqttClient(nullptr) {}

void IDFMQTTManager::setup(const char *mqtt_broker, int mqtt_port,
                           const char *mqtt_username, const char *mqtt_password, bool asAccessPoint)
{
    // Delete old client if exists
    if (_mqttClient != nullptr)
    {
        delete _mqttClient;
    }

    _mqttConfig.broker_uri = "mqtt://" + std::string(mqtt_broker) + ":" + std::to_string(mqtt_port);
    _mqttConfig.client_id = ""; // Let the IDF client generate a unique client ID
    _mqttConfig.username = mqtt_username ? mqtt_username : "";
    _mqttConfig.password = mqtt_password ? mqtt_password : "";

    // Create new client
    _mqttClient = new IDFMQTTClient();

    // Initialize
    bool res = _mqttClient->begin(_mqttConfig);

    if (!res && asAccessPoint)
    {
        Serial.println("Running in Access Point mode. Connect to the AP and use the following IPs:");
        for (const char *ip : IDF_IPs)
        {
            if (!res)
            {
                delete _mqttClient;
                _mqttClient = new IDFMQTTClient();
                _mqttConfig.broker_uri = std::string(ip) + ":" + std::to_string(mqtt_port);
                _mqttClient->setOnMessage(messageCallback);
                res = _mqttClient->begin(_mqttConfig);
            }
        }
    }

    while (_mqttClient->isConnected() == false)
    {
        Serial.println("Waiting for MQTT connection...");
        delay(1000);
    }
}

void IDFMQTTManager::loop(bool pollMqttConnection)
{
    if (_mqttClient != nullptr)
    {
        if (_mqttClient != nullptr && !_mqttClient->isConnected())
        {
            Serial.println("MQTT client not connected. Attempting to reconnect...");
            _mqttClient->end(); // deletes mutex, client_, sets connected_=false

            // Re-create a fresh client and re-register ALL callbacks
            _mqttClient = new IDFMQTTClient();
            _mqttClient->setOnMessage(messageCallback); // ← don't forget this
            _mqttClient->begin(_mqttConfig);

            // Re-subscribe to all topics after reconnecting
            std::map<std::string, int> subscribedTopics = _mqttClient->getSubscribedTopics();
            for (const auto &entry : subscribedTopics)
            {
                _mqttClient->subscribe(entry.first, entry.second);
            }
        }
    }
}

bool IDFMQTTManager::publish(const char *topic, const char *payload, int qos, bool retained)
{
    if (_mqttClient != nullptr)
    {
        int res = _mqttClient->publish(topic, payload, qos, retained);
        if (res != -1)
        {
            return true;
        }
    }
    return false;
}

bool IDFMQTTManager::subscribe(const char *topic, int qos)
{
    if (_mqttClient != nullptr)
    {
        return _mqttClient->subscribe(topic, qos);
    }
    return false;
}

void IDFMQTTManager::messageCallback(const std::string &topic, const std::string &payload)
{
    Serial.print("Message arrived [");
    Serial.print(topic.c_str());
    Serial.print("] ");

    char message[payload.length() + 1];
    for (unsigned int i = 0; i < payload.length(); i++)
    {
        message[i] = (char)payload[i];
    }
    message[payload.length()] = '\0';
    Serial.println(message);
}

bool IDFMQTTManager::publishFileChunkedOverTopics(const char *topic, const char *path, const char *name)
{
    if (_mqttClient == nullptr)
        return false;

    const int MAX_RETRIES = 3;
    for (int attempt = 1; attempt <= MAX_RETRIES; attempt++)
    {
        // Wait for connection
        int waitMs = 0;
        while (!_mqttClient->isConnected() && waitMs < 15000)
        {
            delay(500);
            waitMs += 500;
        }

        if (!_mqttClient->isConnected())
        {
            Serial.printf("Attempt %d/%d: still not connected, skipping\n", attempt, MAX_RETRIES);
            continue;
        }

        bool ok = _mqttClient->publishFileChunkedOverTopics(
            (std::string)topic, path, name, 1, false);

        if (ok)
            return true;

        Serial.printf("Attempt %d/%d failed, retrying...\n", attempt, MAX_RETRIES);
        delay(2000);
    }

    Serial.println("File publish failed after all retries");
    return false;
}

void IDFMQTTManager::disconnect()
{
    if (_mqttClient != nullptr)
    {
        _mqttClient->end();
        delete _mqttClient;
        _mqttClient = nullptr;
    }
}

bool IDFMQTTManager::setCallbackOnMessage(std::function<void(const std::string &topic, const std::string &payload)> callback)
{
    if (_mqttClient != nullptr)
    {
        _mqttClient->setOnMessage(callback);
        return true;
    }
    return false;
}