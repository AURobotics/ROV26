// // idf_mqtt_manager.h
// #ifndef IDF_MQTT_MANAGER_H
// #define IDF_MQTT_MANAGER_H

// #include <Arduino.h>
// #include <IDFMQTTClient.h>

// extern const char *IDF_startingIP;
// extern const char *IDF_IP2;
// extern const char *IDF_IP3;
// extern const char *IDF_IP4;
// extern const char *IDF_IP5;

// extern const char *IDF_IPs[];

// class IDFMQTTManager
// {
// public:
//     IDFMQTTManager();
//     void setup(const char *mqtt_broker, int mqtt_port,
//                const char *mqtt_username, const char *mqtt_password, bool asAccessPoint = false);
//     void loop(bool pollMqttConnection = true);
//     bool publish(const char *topic, const char *payload, int qos = 1, bool retained = false);
//     bool subscribe(const char *topic, int qos = 1);
//     bool publishFileChunkedOverTopics(const char *topic, const char *path, const char *name);
//     bool isConnected() const { return _mqttClient && _mqttClient->isConnected(); }
//     void disconnect();

// private:
//     IDFMQTTClient *_mqttClient;
//     MQTTConfig _mqttConfig;
//     static void messageCallback(const std::string &topic, const std::string &payload);
// };

// #endif