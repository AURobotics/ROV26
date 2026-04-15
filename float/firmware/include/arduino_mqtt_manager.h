// // arduino_mqtt_manager.h
// #ifndef ARDUINO_MQTT_MANAGER_H
// #define ARDUINO_MQTT_MANAGER_H

// #include <Arduino.h>
// #include <ArduinoMQTTClient.h>

// extern const char *startingIP;
// extern const char *IP2;
// extern const char *IP3;
// extern const char *IP4;
// extern const char *IP5;

// extern const char *IPs[];

// class ArduinoMqttManager
// {
// public:
//     ArduinoMqttManager();
//     void setup(const char *mqtt_broker, int mqtt_port,
//                const char *mqtt_username, const char *mqtt_password, bool asAccessPoint = false);
//     void loop(bool pollMqttConnection = true);
//     bool publish(const char *topic, const char *payload, bool retained = false);
//     bool publishFileChunkedOverTopics(const char *topic, const char *filename);

// private:
//     ArduinoMqttClient *_mqttClient;
//     static void messageCallback(char *topic, uint8_t *payload, unsigned int length);
// };

// #endif