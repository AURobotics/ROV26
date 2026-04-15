// #include "arduino_mqtt_manager.h"
// #include <ArduinoMQTTClient.h>
// #include <LittleFS.h>
// #include <rom/crc.h>

// const char *startingIP = "192.168.4.2"; // in case of access point mode, this will be the starting IP of the AP
// const char *IP2 = "192.168.4.3";
// const char *IP3 = "192.168.4.4";
// const char *IP4 = "192.168.4.5";
// const char *IP5 = "192.168.4.6";

// const char *IPs[] = {startingIP, IP2, IP3, IP4, IP5};

// ArduinoMqttManager::ArduinoMqttManager() : _mqttClient(nullptr) {}

// void ArduinoMqttManager::setup(const char *mqtt_broker, int mqtt_port,
//                         const char *mqtt_username, const char *mqtt_password, bool asAccessPoint)
// {
//     // Delete old client if exists
//     if (_mqttClient != nullptr)
//     {
//         delete _mqttClient;
//     }

//     // Create new client
//     _mqttClient = new ArduinoMqttClient(mqtt_broker, mqtt_port, mqtt_username, mqtt_password);

//     // Set callback
//     _mqttClient->setCallback(messageCallback);

//     // Initialize
//     bool res = _mqttClient->begin();

//     if (!res && asAccessPoint)
//     {
//         Serial.println("Running in Access Point mode. Connect to the AP and use the following IPs:");
//         for (const char *ip : IPs)
//         {
//             if (!res)
//             {
//                 delete _mqttClient;
//                 _mqttClient = new ArduinoMqttClient(ip, mqtt_port, mqtt_username, mqtt_password);
//                 _mqttClient->setCallback(messageCallback);
//                 res = _mqttClient->begin();
//             }
//         }
//     }
// }

// void ArduinoMqttManager::loop(bool pollMqttConnection)
// {
//     if (_mqttClient != nullptr)
//     {
//         _mqttClient->loop(pollMqttConnection);
//     }
// }

// bool ArduinoMqttManager::publish(const char *topic, const char *payload, bool retained)
// {
//     if (_mqttClient != nullptr)
//     {
//         return _mqttClient->publish(topic, payload, retained);
//     }
//     return false;
// }

// void ArduinoMqttManager::messageCallback(char *topic, uint8_t *payload, unsigned int length)
// {
//     Serial.print("Message arrived [");
//     Serial.print(topic);
//     Serial.print("] ");

//     char message[length + 1];
//     for (unsigned int i = 0; i < length; i++)
//     {
//         message[i] = (char)payload[i];
//     }
//     message[length] = '\0';
//     Serial.println(message);
// }

// uint32_t calculateCRC32(const uint8_t *data, size_t length)
// {
//     return ~crc32_le(~0, data, length);
// }

// bool ArduinoMqttManager::publishFileChunkedOverTopics(const char *topic, const char *filename)
// {
//     if (_mqttClient != nullptr)
//     {
//         return _mqttClient->publishFileChunkedOverTopics((FS &)LittleFS, topic, filename, nullptr);
//     }
//     return false;
// }