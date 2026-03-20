
#include "ESPMqttClient.h"

// libraries used for method sending in chunks
#include <FS.h> // For file system operations
#include <SPIFFS.h>
#include <ArduinoJson.h>
#include <Base64.h> // For encoding binary data to base64

ESPMqttClient::ESPMqttClient(
    const char *mqtt_server,
    int mqtt_port,
    const char *mqtt_username,
    const char *mqtt_password) : _mqtt_broker(mqtt_server),
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

/**
 * called in setup() to initialize the MQTT client and connect to the broker.
 * Sets up the MQTT server address and registers a lambda as the internal callback
 */
void ESPMqttClient::begin()
{
    _mqttClient.setServer(_mqtt_broker, _mqtt_port);
    // Register a lambda as the internal PubSubClient callback.
    // It captures 'this' so it can forward calls to the user-supplied _callback.

    _mqttClient.setCallback([this](char *topic, byte *payload, unsigned int length)
                            {
        // Only invoke the user callback if one has actually been registered
        if (_callback) {
            _callback(topic, payload, length);
        } });
    connectToMQTT();
}

/**
 * This method should be called repeatedly in the main loop() function.
 * It checks if the MQTT connection is still alive, and if not, it attempts to reconnect.
 * Then it calls the loop() method of the underlying PubSubClient to handle incoming messages,
 */
void ESPMqttClient::loop(bool pollMqttConnection)
{
    // If MQTT connection has dropped, attempt to reconnect
    if (!_mqttClient.connected())
    {
        connectToMQTT(pollMqttConnection);
    }

    // Allow PubSubClient to process network traffic (keep-alive pings,
    // incoming message dispatch, QoS acknowledgements, etc.)
    _mqttClient.loop();
}

void ESPMqttClient::connectToMQTT(bool poll)
{
    while (!_mqttClient.connected())
    {
        String client_id = "esp32-client-";
        client_id += String(WiFi.macAddress()); // to ensure unique id
        Serial.printf("The client %s connects to the MQTT broker\n", client_id.c_str());
        bool isConnected = false;
        if (_mqtt_username && _mqtt_password)
        {
            isConnected = _mqttClient.connect(client_id.c_str(), _mqtt_username, _mqtt_password);
        }
        else
        {
            isConnected = _mqttClient.connect(client_id.c_str());
        }

        if (isConnected)
        {
            Serial.println("broker connected");

            // Re-subscribe to all previously subscribed topics after reconnecting
            if (!_subscribed_topics.empty())
            {
                for (const auto &topic : _subscribed_topics)
                {
                    if (_mqttClient.subscribe(topic.c_str()))
                    {
                        Serial.printf("Subscribed to topic: %s\n", topic.c_str());
                    }
                    else
                    {
                        Serial.printf("Failed to subscribe to topic: %s\n", topic.c_str());
                    }
                }
            }
        }
        else
        {
            Serial.print("failed with state ");
            Serial.println(_mqttClient.state());
            if (!poll)
            {
                Serial.println("Not polling for MQTT connection. Exiting connect loop.");
                return;
            }
            delay(2000);
        }
    }
}

/**
 * @param topic The MQTT topic to publish to (e.g. "sensors/temperature")
 * @param payload The message content to send (null-terminated string)
 * @param retained If true, the broker will store this message and deliver it
 *                 to future subscribers immediately upon subscription
 * @returns true on success, false if not connected or message too large
 */
bool ESPMqttClient::publish(const char *topic, const char *payload, bool retained)
{
    return _mqttClient.publish(topic, payload, retained);
}

/**
 * Subscribes to an MQTT topic to receive messages published to it.
 * The registered callback (setCallback) will be invoked for each incoming message.
 * @returns true on success, false if not connected or subscription failed.
 */
bool ESPMqttClient::subscribe(const char *topic)
{
    std::string t(topic);
    // avoid duplicate entries
    if (std::find(_subscribed_topics.begin(), _subscribed_topics.end(), t) == _subscribed_topics.end())
    {
        _subscribed_topics.push_back(t);
    }
    return _mqttClient.subscribe(topic);
}

/**
 * Unsubscribes from an MQTT topic.
 * @returns true on success, false if not connected or unsubscription failed.
 */
bool ESPMqttClient::unsubscribe(const char *topic)
{
    if (!_mqttClient.connected())
    {
        Serial.println("Cannot unsubscribe, MQTT client not connected");
        return false;
    }
    _subscribed_topics.erase(std::remove(_subscribed_topics.begin(), _subscribed_topics.end(), std::string(topic)), _subscribed_topics.end());
    return _mqttClient.unsubscribe(topic);
}

/** 
 * @returns true if the client currently has an active MQTT broker connection.
 */
bool ESPMqttClient::isConnected()
{
    return _mqttClient.connected();
}

/**
 * Gracefully disconnects from the MQTT broker and then from WiFi.
 * Called automatically by the destructor.
 */
void ESPMqttClient::disconnect()
{
    // Clear the list of subscribed topics since we're disconnecting
    _subscribed_topics.clear();

    _mqttClient.disconnect();
    WiFi.disconnect();
}

/**
 * Registers a user-defined callback function to handle incoming MQTT messages.
 *
 * @param callback A function with signature:
 *                 void callback(char* topic, uint8_t* payload, unsigned int length)
 *                 that will be called whenever a message is received on a subscribed topic.
 *                 @param topic Null-terminated string of the topic the message was received on.
 *                 @param payload Raw message bytes (not null-terminated).
 *                 @param length Number of bytes in the payload.
 */
void ESPMqttClient::setCallback(std::function<void(char *, uint8_t *, unsigned int)> callback)
{
    _callback = callback;
}


/**
 * send file in chunks over MQTT.
 *
 * This is necessary because MQTT has a maximum payload size (256-512 bytes ).
 * sending the file in smaller chunks -> ensure that we don't exceed this limit
 *
 * This is the main function for sending files. It:
 * 1. Opens the file and gets its size
 * 2. Calculates number of chunks needed
 * 3. Sends metadata (file info) first
 * 4. Sends the file data in chunks
 *
 * Chunks are base64 encoded to ensure binary data can be sent over MQTT's text-based protocol.
 *
 * Chuncks are sent in diffrenet subtopics (format: "base_topic/chunk/chunk_number")
 * (e.g. "base_topic/chunk/0", "base_topic/chunk/1", etc.) to allow receiver to reconstruct the file in order.
 *
 * @param topic Base MQTT topic for the file transfer
 * @param filename Path to the file to send
 * @return true if file sent successfully, false otherwise
 */
bool ESPMqttClient::sendFileChunked(const char *topic, const char *filename)
{
    base64 base64_encoder = base64();
    File file = SPIFFS.open(filename, "r");
    if (!file)
    {
        Serial.print("Failed to open file: ");
        Serial.println(filename);
        return false;
    }

    Serial.print("Opening file: ");
    Serial.print(filename);
    Serial.print(" | Size: ");
    Serial.print(file.size());
    Serial.println(" bytes");

    // Calculate chunks
    const int CHUNK_SIZE = 512; // 512 bytes to work with mqtt limits
    size_t fileSize = file.size();
    int totalChunks = (fileSize + CHUNK_SIZE - 1) / CHUNK_SIZE; // ceiling division

    Serial.print(totalChunks);
    Serial.println(" chunks");

    // Send file metadata first
    // - filename: name of file
    // - size: total bytes
    // - chunks: number of chunks
    // - encoding: how the data is encoded (base64 in this case)

    char metaTopic[128];
    snprintf(metaTopic, sizeof(metaTopic), "%s/meta", topic);

    StaticJsonDocument<256> metaDoc;
    metaDoc["filename"] = filename;
    metaDoc["size"] = fileSize;
    metaDoc["chunks"] = totalChunks;
    metaDoc["encoding"] = "base64"; // Tell receiver we're using base64

    String metadata;
    serializeJson(metaDoc, metadata);

    Serial.print("Sending metadata: ");
    Serial.println(metadata);

    if (!publish(metaTopic, metadata.c_str(), false))
    {
        Serial.println("Failed to send metadata");
        file.close();
        return false;
    }

    delay(50); // Small delay to let receiver process metadata

    // buffer for reading file
    uint8_t buffer[CHUNK_SIZE]; // Raw file data buffer
    int bytesRead;
    bool success = true;

    // Send each chunk
    for (int chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++)
    {
        // Read a chunk from the file
        bytesRead = file.read(buffer, CHUNK_SIZE);

        if (bytesRead <= 0)
        {
            Serial.print("Unexpected end of file at chunk ");
            Serial.println(chunkIndex);
            success = false;
            break;
        }

        // calculate base64 encoded size: ((bytesRead + 2) / 3) * 4
        int encodedLen = ((bytesRead + 2) / 3) * 4;
        String encodedData;

        // encode the binary chunk to base64
        encodedData = base64_encoder.encode((const uint8_t *)buffer, bytesRead);

        // chunk-specific topic
        // format: base_topic/chunk/chunk_number
        // e.g. "float/data/chunk/0", "float/data/chunk/1", etc.
        char chunkTopic[128];
        snprintf(chunkTopic, sizeof(chunkTopic), "%s/chunk/%d", topic, chunkIndex);

        // Send the chunk
        // Each chunk contains base64 encoded data
        if (!publish(chunkTopic, encodedData.c_str(), false))
        {
            Serial.print("Failed to send chunk ");
            Serial.println(chunkIndex);
            success = false;
            break;
        }

        // Print progress
        Serial.print("Sent chunk ");
        Serial.print(chunkIndex + 1);
        Serial.print("/");
        Serial.print(totalChunks);
        Serial.print(" (");
        Serial.print(bytesRead);
        Serial.println(" bytes)");

        // Small delay between chunks to avoid flooding MQTT broker
        delay(10);
    }

    file.close();

    if (success)
        Serial.println("File transfer completed successfully!");
    else
        Serial.println("File transfer failed!");

    return success;
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