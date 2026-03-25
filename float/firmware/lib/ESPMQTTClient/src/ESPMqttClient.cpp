
#include "ESPMqttClient.h"

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
 *
 * @returns true if connection to MQTT broker is successful, false otherwise
 */
bool ESPMqttClient::begin()
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
    return connectToMQTT();
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

bool ESPMqttClient::connectToMQTT(bool poll)
{
    while (!_mqttClient.connected())
    {
        String client_id = "esp32-client-";
        client_id += String(WiFi.macAddress()); // to ensure unique id
        // Serial.printf("The client %s connects to the MQTT broker\n", client_id.c_str());
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
            // Serial.println("broker connected");

            // Re-subscribe to all previously subscribed topics after reconnecting
            if (!_subscribed_topics.empty())
            {
                for (const auto &topic : _subscribed_topics)
                {
                    if (_mqttClient.subscribe(topic.c_str()))
                    {
                        // Serial.printf("Subscribed to topic: %s\n", topic.c_str());
                    }
                    else
                    {
                        // Serial.printf("Failed to subscribe to topic: %s\n", topic.c_str());
                    }
                }
            }
        }
        else
        {
            // Serial.print("failed with state ");
            // Serial.println(_mqttClient.state());
            if (!poll)
            {
                // Serial.println("Not polling for MQTT connection. Exiting connect loop.");
                return false;
            }
            delay(2000);
        }
    }
    return true;
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
        // Serial.println("Cannot unsubscribe, MQTT client not connected");
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
 * if crcCalculator is provided, it will be used to calculate CRC32 checksums metadata and each chunk
 * crc value is appended to the end of the base64 encoded string in hex format.
 * receiver must account that the last 8 characters of the encoded chunk are the CRC32 checksum (if crcCalculator is used)
 *
 * @param fileSystem Reference to the filesystem (e.g. SPIFFS) where the file is located
 * @param topic Base MQTT topic for the file transfer
 * @param filename Path to the file to send
 * @param crcCalculator Optional function pointer to calculate CRC32 checksums. If provided, CRC32 of the entire file will be included in metadata, and each chunk will have its own CRC32 appended to the end of the encoded data.
 *
 * @return true if file sent successfully, false otherwise
 */
bool ESPMqttClient::sendFileChunkedOverTopics(FS &fileSystem, const char *topic, const char *filename, CRC32Function crcCalculator)
{
    base64 base64_encoder = base64();
    uint32_t calculatedCRC = 0;

    File file = fileSystem.open(filename, "r");
    if (!file)
    {
        // Serial.print("Failed to open file: ");
        // Serial.println(filename);
        return false;
    }

    // Serial.print("Opening file: ");
    // Serial.print(filename);
    // Serial.print(" | Size: ");
    // Serial.print(file.size());
    // Serial.println(" bytes");

    // Calculate chunks
    // originally 180 bytes -> 240 bytes in base64; but that failed
    int RAW_CHUNK_SIZE;
    if (crcCalculator)
        RAW_CHUNK_SIZE = 150 - 6; // leave room for CRC32
    else
        RAW_CHUNK_SIZE = 150;
    size_t fileSize = file.size();
    int totalChunks = (fileSize + RAW_CHUNK_SIZE - 1) / RAW_CHUNK_SIZE; // ceiling division

    // Serial.print(totalChunks);
    // Serial.println(" chunks");

    // Send file metadata first
    // - filename: name of file
    // - size: total bytes
    // - chunks: number of chunks
    // - encoding: how the data is encoded (base64 in this case)

    char metaTopic[128];
    snprintf(metaTopic, sizeof(metaTopic), "%s/meta", topic);

    StaticJsonDocument<256> metaDoc;
    metaDoc["filename"] = filename;
    if (crcCalculator)
        metaDoc["size"] = fileSize + 8 * (totalChunks + 1); // account for CRC32 checksums (8 hex chars) in metadata and each chunk
    else
        metaDoc["size"] = fileSize;
    metaDoc["chunks"] = totalChunks;
    metaDoc["encoding"] = "base64"; // Tell receiver we're using base64

    String metadata;
    serializeJson(metaDoc, metadata);

    // if crc, calculate CRC32 of the file and include it in metadata
    if (crcCalculator)
    {
        calculatedCRC = crcCalculator((const uint8_t *)metadata.c_str(), metadata.length());
        // Serial.print("Calculated CRC32 for metadata: ");
        // Serial.println(calculatedCRC, HEX);

        char crcHex[9];                         // 8 hex chars + null terminator
        snprintf(crcHex, sizeof(crcHex), "%08X", calculatedCRC);
        metadata += crcHex;
    }

    // Serial.print("Sending metadata: ");
    // Serial.println(metadata);

    if (!publish(metaTopic, metadata.c_str(), false))
    {
        // Serial.println("Failed to send metadata");
        file.close();
        return false;
    }

    delay(50); // Small delay to let receiver process metadata

    // buffer for reading file
    uint8_t buffer[RAW_CHUNK_SIZE]; // Raw file data buffer
    int bytesRead;
    bool success = true;

    // Send each chunk
    for (int chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++)
    {
        // Read a chunk from the file
        bytesRead = file.read(buffer, RAW_CHUNK_SIZE);

        if (bytesRead <= 0)
        {
            // Serial.print("Unexpected end of file at chunk ");
            // Serial.println(chunkIndex);
            success = false;
            break;
        }

        // calculate base64 encoded size: ((bytesRead + 2) / 3) * 4
        String encodedData;

        // encode the binary chunk to base64
        encodedData = base64_encoder.encode((const uint8_t *)buffer, bytesRead);

        // chunk-specific topic
        // format: base_topic/chunk/chunk_number
        // e.g. "float/data/chunk/0", "float/data/chunk/1", etc.
        char chunkTopic[128];
        snprintf(chunkTopic, sizeof(chunkTopic), "%s/chunk/%d", topic, chunkIndex);

        if (crcCalculator)
        {
            // If CRC is enabled, append the CRC32 of this chunk to the end of the encoded data
            uint32_t chunkCRC = crcCalculator(buffer, bytesRead);
            // Serial.print("Calculated CRC32 for chunk ");
            // Serial.print(chunkIndex);
            // Serial.print(": ");
            // Serial.println(chunkCRC, HEX);
            
            char crcHex[9]; // 8 hex chars + null terminator
            snprintf(crcHex, sizeof(crcHex), "%08X", chunkCRC);
            encodedData += crcHex;
        }

        // Send the chunk
        // Each chunk contains base64 encoded data
        if (!publish(chunkTopic, encodedData.c_str(), false))
        {
            // Serial.print("Failed to send chunk ");
            // Serial.println(chunkIndex);
            // Serial.print("chunk size (encoded): ");
            // Serial.println(encodedData.length());
            success = false;
            break;
        }

        // Print progress
        // Serial.print("Sent chunk ");
        // Serial.print(chunkIndex + 1);
        // Serial.print("/");
        // Serial.print(totalChunks);
        // Serial.print(" (");
        // Serial.print(bytesRead);
        // Serial.println(" bytes)");

        // Small delay between chunks to avoid flooding MQTT broker
        delay(10);
    }

    file.close();

    return success;
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
 * after sending each chunk it waits for a feedback message from the receiver (on topic "base_topic/feedback") before sending the next chunk.
 *
 * if crcCalculator is provided, it will be used to calculate CRC32 checksums metadata and each chunk
 * crc value is appended to the end of the base64 encoded string in hex format.
 * receiver must account that the last 8 characters of the encoded chunk are the CRC32 checksum (if crcCalculator is used)
 *
 * @param fileSystem Reference to the filesystem (e.g. SPIFFS) where the file is located
 * @param topic Base MQTT topic for the file transfer
 * @param filename Path to the file to send
 * @param crcCalculator Optional function pointer to calculate CRC32 checksums. If provided, CRC32 of the entire file will be included in metadata, and each chunk will have its own CRC32 appended to the end of the encoded data.
 *
 * @return true if file sent successfully, false otherwise
 */
bool ESPMqttClient::sendFileChunkedWithFeedback(FS &fileSystem, const char *topic, const char *filename, CRC32Function crcCalculator)
{
    return false;
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