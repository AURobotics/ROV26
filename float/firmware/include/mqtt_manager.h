// mqtt_manager.h
#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <Arduino.h>
#include <ESPMqttClient.h>

class MQTTManager
{
public:
    MQTTManager();
    void setup(const char *mqtt_broker, int mqtt_port,
               const char *mqtt_username, const char *mqtt_password);
    void loop();
    bool publish(const char *topic, const char *payload, bool retained = false);

private:
    ESPMqttClient *_mqttClient;
    static void messageCallback(char *topic, uint8_t *payload, unsigned int length);
};

#endif