
#include "ESPMqttClient.h"

ESPMqttClient::ESPMqttClient(
    const char *ssid,
    const char *password,
    const char *mqtt_server,
    int mqtt_port,
    const char *mqtt_username,
    const char *mqtt_password,
    const bool as_AccessPoint) :   _ssid(ssid),
                                   _password(password),
                                   _as_AccessPoint(as_AccessPoint),
                                   _mqtt_broker(mqtt_server),
                                   _mqtt_port(mqtt_port),
                                   _mqtt_username(mqtt_username),
                                   _mqtt_password(mqtt_password),
                                   _mqttClient(_wifiClient)
{
}

ESPMqttClient::~ESPMqttClient()
{
    disconnect();
}

// =============================================================================
// begin()
// Must be called once in the Arduino setup() function.
// Initializes Serial, connects to WiFi, configures the MQTT broker address,
// and registers the internal message callback dispatcher.
// =============================================================================
void ESPMqttClient::begin()
{
    Serial.begin(115200);

    if (_as_AccessPoint)
    {
        initAccessPoint();
    }
    else
    {
        connectToWiFi();
    }

    _mqttClient.setServer(_mqtt_broker, _mqtt_port);
    // Register a lambda as the internal PubSubClient callback.
    // It captures 'this' so it can forward calls to the user-supplied _callback.

    _mqttClient.setCallback([this](char *topic, byte *payload, unsigned int length)
                            {
        // Only invoke the user callback if one has actually been registered
        if (_callback) {
            _callback(topic, payload, length);
        } });
}

// =============================================================================
// loop()
// Must be called repeatedly inside the Arduino loop() function.
// Checks the MQTT connection state and reconnects if necessary, then
// hands control to PubSubClient to process incoming/outgoing messages.
// =============================================================================
void ESPMqttClient::loop()
{
    // Ensure WiFi is still connected before checking MQTT state
    if (!_as_AccessPoint && WiFi.status() != WL_CONNECTED)
    {
        Serial.println("WiFi connection lost. Reconnecting...");
        connectToWiFi();
    }

    // If MQTT connection has dropped, attempt to reconnect
    if (!_mqttClient.connected())
    {
        connectToMQTT();
    }

    // Allow PubSubClient to process network traffic (keep-alive pings,
    // incoming message dispatch, QoS acknowledgements, etc.)
    _mqttClient.loop();
}

void ESPMqttClient::connectToWiFi()
{
    Serial.print("Connecting to WiFi");
    WiFi.begin(_ssid, _password);

    // Poll every 500ms until connected
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print("Connecting to WiFi..");
    }

    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

void ESPMqttClient::initAccessPoint(){
    IPAddress local_IP(192, 168, 1, 22);
    IPAddress gateway(192, 168, 1, 5);
    IPAddress subnet(255, 255, 255, 0);

    Serial.print("Setting up Access Point ... ");
    Serial.println(WiFi.softAPConfig(local_IP, gateway, subnet) ? "Ready" : "Failed!");

    Serial.print("Starting Access Point ... ");
    Serial.println(WiFi.softAP(_ssid, _password) ? "Ready" : "Failed!");

    Serial.print("IP address = ");
    Serial.println(WiFi.softAPIP());
}

void ESPMqttClient::connectToMQTT()
{
    while (!_mqttClient.connected())
    {
        String client_id = "esp32-client-";
        client_id += String(WiFi.macAddress()); // to ensure unique id
        Serial.printf("The client %s connects to the public MQTT broker\n", client_id.c_str());
        if (_mqttClient.connect(client_id.c_str(), _mqtt_username, _mqtt_password))
        {
            Serial.println("Public EMQX MQTT broker connected");
        }
        else
        {
            Serial.print("failed with state ");
            Serial.print(_mqttClient.state());
            delay(2000);
        }
    }
}

// =============================================================================
// publish()
// Publishes a message payload to the specified MQTT topic.
//
// Parameters:
//   topic    - The MQTT topic string to publish to
//   payload  - The message content (null-terminated string)
//   retained - If true, the broker stores the last message and delivers it
//              to future subscribers immediately upon subscription
//
// Returns true on success, false if not connected or the message was too large.
// =============================================================================
bool ESPMqttClient::publish(const char *topic, const char *payload, bool retained)
{
    return _mqttClient.publish(topic, payload, retained);
}

// =============================================================================
// subscribe()
// Subscribes to an MQTT topic to receive messages published to it.
// The registered callback (setCallback) will be invoked for each incoming message.
//
// Returns true on success, false if not connected or subscription failed.
// =============================================================================
bool ESPMqttClient::subscribe(const char *topic)
{
    return _mqttClient.subscribe(topic);
}

// =============================================================================
// unsubscribe()
// Cancels an existing subscription to the specified MQTT topic.
//
// Returns true on success, false if not connected or unsubscription failed.
// =============================================================================
bool ESPMqttClient::unsubscribe(const char *topic)
{
    return _mqttClient.unsubscribe(topic);
}

// =============================================================================
// isConnected()
// Returns true if the client currently has an active MQTT broker connection.
// =============================================================================
bool ESPMqttClient::isConnected()
{
    return _mqttClient.connected();
}

// =============================================================================
// disconnect()
// Gracefully disconnects from the MQTT broker and then from WiFi.
// Called automatically by the destructor.
// =============================================================================
void ESPMqttClient::disconnect()
{
    _mqttClient.disconnect();
    WiFi.disconnect();
}

// =============================================================================
// setCallback()
// Registers a user-defined function to handle incoming MQTT messages.
// Must be called before begin() or at least before any subscriptions are made.
//
// The callback signature must be:
//   void myCallback(char* topic, uint8_t* payload, unsigned int length)
//
//   topic   - Null-terminated topic string the message arrived on
//   payload - Raw message bytes (NOT null-terminated; use 'length' to read it)
//   length  - Number of bytes in the payload
// =============================================================================
void ESPMqttClient::setCallback(std::function<void(char *, uint8_t *, unsigned int)> callback)
{
    _callback = callback;
}

// =#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
// =#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#

// for future extension if needed instead of using the setCallback

// #include <sstream>

// MqttMessage::MqttMessage() : args() {}

// void MqttMessage::addVariable(const std::string &name, const std::any &value)
// {
//     args[name] = value;
// }

// void MqttMessage::setVariable(const std::string &name, const std::any &value)
// {
//     auto it = args.find(name);
//     if (it != args.end())
//     {
//         it->second = value;
//     }
//     else
//     {
//         throw std::runtime_error("Variable '" + name + "' not found in message arguments.");
//     }
// }

// bool MqttMessage::hasVariable(const std::string &name) const
// {
//     return args.find(name) != args.end();
// }

// // Encode to JSON string
// std::string MqttMessage::encode() const
// {
//     const size_t capacity = 1024;
//     DynamicJsonDocument doc(capacity);
//     JsonObject obj = doc.to<JsonObject>();

//     for (const auto &[key, value] : args)
//     {
//         obj[key] = value;
//     }

//     std::string output;
//     serializeJson(doc, output);
//     return output;
// }

// // Decode from JSON string
// void MqttMessage::decode(const std::string &payload)
// {
//     const size_t capacity = 1024;
//     DynamicJsonDocument doc(capacity);

//     DeserializationError error = deserializeJson(doc, payload);
//     if (error)
//     {
//         return;
//     }

//     args.clear();
//     JsonObject obj = doc.as<JsonObject>();
//     for (JsonPair kv : obj)
//     {
//         args[kv.key().c_str()] = kv.value();
//     }
// }

// // Example derived class for specific message types
// /*
// class TemperatureMessage : public MqttMessage {
// public:
//     TemperatureMessage() {
//         addVariable("temperature", 0.0f);
//         addVariable("unit", std::string("C"));
//         addVariable("timestamp", 0L);
//     }

//     void setTemperature(float temp) {
//         setVariable("temperature", temp);
//     }

//     float getTemperature() const {
//         return getVariable<float>("temperature");
//     }
// };
// */