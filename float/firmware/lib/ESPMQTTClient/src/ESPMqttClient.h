#ifndef ESP_MQTT_CLIENT_H
#define ESP_MQTT_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
// #include <ArduinoJson.h>
// #include <map>
// #include <string>
// #include <any>
// #include <stdexcept>
// #include <functional>

class ESPMqttClient
{
public:
    // Constructor
    ESPMqttClient(
        const char *mqtt_broker,
        int mqtt_port = 1883,
        const char *mqtt_username = nullptr,
        const char *mqtt_password = nullptr);

    // Destructor
    ~ESPMqttClient();

    // Public methods
    void begin();
    void loop(bool pollMqttConnection = true);
    bool publish(const char *topic = "test", const char *payload = "publishing to \"test\"", bool retained = false);
    bool subscribe(const char *topic = "test");
    bool unsubscribe(const char *topic);
    bool isConnected();
    void disconnect();
    void setCallback(std::function<void(char *, uint8_t *, unsigned int)> callback);
    bool sendFileChunked(const char *topic, const char *filename);

private:
    // WiFi
    const char *_ssid;
    const char *_password;

    // MQTT Broker
    const char *_mqtt_broker;
    const char *_mqtt_username;
    const char *_mqtt_password;
    const int _mqtt_port;

    // subscribed topics
    std::vector<std::string> _subscribed_topics;


    // WiFi and MQTT clients
    WiFiClient _wifiClient;
    PubSubClient _mqttClient;

    // Callback function
    std::function<void(char *, uint8_t *, unsigned int)> _callback;

    // Private methods
    void connectToMQTT(bool poll = true);
};

// for future extension if needed instead of using the setCallback

// class MqttMessage
// {
// public:
//     MqttMessage();
//     ~MqttMessage();

//     // Add a new variable to the message
//     void addVariable(const std::string &name, const std::any &value);

//     // Set an existing variable's value
//     void setVariable(const std::string &name, const std::any &value);

//     // Encode message to JSON string for MQTT payload
//     std::string encode() const;

//     // Decode MQTT payload to message arguments
//     void decode(const std::string &payload);

//     // Check if a variable exists
//     bool hasVariable(const std::string &name) const;

//     // Get variable value with type checking
//     template <typename T>
//     T getVariable(const std::string &name) const
//     {
//         auto it = args.find(name);
//         if (it == args.end())
//         {
//             throw std::runtime_error("Variable '" + name + "' not found");
//         }

//         try
//         {
//             return std::any_cast<T>(it->second);
//         }
//         catch (const std::bad_any_cast &e)
//         {
//             throw std::runtime_error("Type mismatch for variable '" + name + "'");
//         }
//     }

// protected:
//     std::map<std::string, std::any> args;
// };

#endif