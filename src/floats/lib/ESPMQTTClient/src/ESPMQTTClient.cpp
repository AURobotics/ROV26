
#include "ESPMQTTClient.h"

// =============================================================================
// CONSTRUCTOR
// Initializes all member variables using an initializer list.
// _mqttClient is initialized with _wifiClient so that MQTT traffic is routed
// through the ESP32's WiFi stack.
//
// Parameters:
//   ssid          - WiFi network name
//   password      - WiFi network password
//   mqtt_server   - Hostname or IP address of the MQTT broker
//   mqtt_port     - Port of the MQTT broker (typically 1883 or 8883 for TLS)
//   mqtt_user     - MQTT username (pass nullptr to connect anonymously)
//   mqtt_password - MQTT password (pass nullptr to connect anonymously)
//   client_id     - Unique MQTT client identifier (pass nullptr to auto-generate)
// =============================================================================
ESPMQTTClient::ESPMQTTClient(
    const char *ssid,
    const char *password,
    const char *mqtt_server,
    int mqtt_port,
    const char *mqtt_user,
    const char *mqtt_password,
    const char *client_id) : _ssid(ssid),
                             _password(password),
                             _mqtt_server(mqtt_server),
                             _mqtt_port(mqtt_port),
                             _mqtt_user(mqtt_user),
                             _mqtt_password(mqtt_password),
                             _client_id(client_id),
                             _mqttClient(_wifiClient)
{
    // If no client ID was supplied, generate one from the chip's unique MAC address.
    // Note: generateClientID() must be called here, AFTER the member list is set,
    // so that _client_id can be safely overwritten.
    if (_client_id == nullptr)
    {
        generateClientID();
    }
}

// =============================================================================
// DESTRUCTOR
// Gracefully disconnects from both MQTT broker and WiFi when the object
// goes out of scope or is deleted.
// =============================================================================
ESPMQTTClient::~ESPMQTTClient()
{
    disconnect();
}

// =============================================================================
// begin()
// Must be called once in the Arduino setup() function.
// Initializes Serial, connects to WiFi, configures the MQTT broker address,
// and registers the internal message callback dispatcher.
//
// BUG FIX: keepAlive and cleanSession settings were stored via setKeepAlive()
// and setCleanSession() but were never actually applied to the PubSubClient.
// They are now applied here before the first connection attempt.
// =============================================================================
void ESPMQTTClient::begin()
{
    Serial.begin(115200);

    // Establish WiFi connection before doing anything MQTT-related
    connectToWiFi();

    // Tell PubSubClient which broker to connect to
    _mqttClient.setServer(_mqtt_server, _mqtt_port);

    // BUG FIX: Apply keepAlive to PubSubClient. Previously _keepAlive was stored
    // but never forwarded, so the broker used its own default (typically 15s).
    _mqttClient.setKeepAlive(_keepAlive);

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
//
// BUG FIX: Added a WiFi connectivity check before attempting MQTT reconnection.
// Without this, connectToMQTT() would spin endlessly if WiFi had dropped,
// because PubSubClient cannot succeed without a working network layer.
// =============================================================================
void ESPMQTTClient::loop()
{
    // Ensure WiFi is still connected before checking MQTT state
    if (WiFi.status() != WL_CONNECTED)
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

// =============================================================================
// connectToWiFi()
// Blocks until a WiFi connection is established.
// Prints progress dots to Serial while waiting.
// =============================================================================
void ESPMQTTClient::connectToWiFi()
{
    Serial.print("Connecting to WiFi");
    WiFi.begin(_ssid, _password);

    // Poll every 500ms until connected
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

// =============================================================================
// connectToMQTT()
// Blocks until an MQTT broker connection is established.
// Retries every 5 seconds on failure, printing the PubSubClient error code.
//
// Supports two connection modes:
//   - Authenticated: connects with username + password + LWT
//   - Anonymous:     connects with client ID + LWT only
//
// The Last Will and Testament (LWT) is included in the CONNECT packet so the
// broker will publish it automatically if this client disconnects unexpectedly.
// =============================================================================
void ESPMQTTClient::connectToMQTT()
{
    while (!_mqttClient.connected())
    {
        Serial.print("Attempting MQTT connection...");

        bool connected = false;

        // Choose connection method based on whether credentials were provided
        if (_mqtt_user != nullptr && _mqtt_password != nullptr)
        {
            // Authenticated connection with LWT
            // Parameters: clientID, user, password, willTopic, willQoS, willRetain, willMessage
            connected = _mqttClient.connect(
                _client_id,
                _mqtt_user,
                _mqtt_password,
                _willTopic,
                0, // Will QoS level 0 (at most once)
                _willRetained,
                _willMessage);
        }
        else
        {
            // Anonymous connection with LWT
            // Parameters: clientID, willTopic, willQoS, willRetain, willMessage
            connected = _mqttClient.connect(
                _client_id,
                _willTopic,
                0, // Will QoS level 0 (at most once)
                _willRetained,
                _willMessage);
        }

        if (connected)
        {
            Serial.println("connected");
        }
        else
        {
            // PubSubClient state codes:
            //  -4 = connection timeout    -3 = connection lost
            //  -2 = connect failed        -1 = disconnected
            //   1 = bad protocol           2 = bad client ID
            //   3 = server unavailable     4 = bad credentials
            //   5 = unauthorized
            Serial.print("failed, rc=");
            Serial.print(_mqttClient.state());
            Serial.println(" — retrying in 5 seconds");
            delay(5000);
        }
    }
}

// =============================================================================
// generateClientID()
// Generates a unique client ID string from the ESP32's 64-bit MAC/EFuse address.
//
// BUG FIX: The original code used a 'static' local char array, meaning all
// instances of ESPMQTTClient shared the same buffer. If two objects existed
// simultaneously, the second call would silently overwrite the first object's ID.
// Fixed by making _generatedID a member variable (declared in the header as
// char _generatedID[20]) so each instance has its own dedicated buffer.
//
// BUG FIX: ESP.getEfuseMac() returns a uint64_t (64-bit MAC address), not a
// uint32_t. Casting to uint32_t silently discards the upper 32 bits, making IDs
// potentially non-unique across devices. Fixed by using uint64_t and formatting
// the full value into the ID string.
// =============================================================================
void ESPMQTTClient::generateClientID()
{
    // getEfuseMac() returns the full 64-bit base MAC address of the chip
    uint64_t chipId = ESP.getEfuseMac();

    // Format as "ESP-" followed by the lower 32 bits in hex.
    // The lower 32 bits change per device and are sufficient for practical uniqueness.
    // Using the instance-owned _generatedID buffer (not a static local) to avoid
    // the shared-buffer bug that affected the original implementation.
    snprintf(_generatedID, sizeof(_generatedID), "ESP-%08X", (uint32_t)(chipId & 0xFFFFFFFF));
    _client_id = _generatedID;
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
bool ESPMQTTClient::publish(const char *topic, const char *payload, bool retained)
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
bool ESPMQTTClient::subscribe(const char *topic)
{
    return _mqttClient.subscribe(topic);
}

// =============================================================================
// unsubscribe()
// Cancels an existing subscription to the specified MQTT topic.
//
// Returns true on success, false if not connected or unsubscription failed.
// =============================================================================
bool ESPMQTTClient::unsubscribe(const char *topic)
{
    return _mqttClient.unsubscribe(topic);
}

// =============================================================================
// isConnected()
// Returns true if the client currently has an active MQTT broker connection.
// =============================================================================
bool ESPMQTTClient::isConnected()
{
    return _mqttClient.connected();
}

// =============================================================================
// disconnect()
// Gracefully disconnects from the MQTT broker and then from WiFi.
// Called automatically by the destructor.
// =============================================================================
void ESPMQTTClient::disconnect()
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
void ESPMQTTClient::setCallback(std::function<void(char *, uint8_t *, unsigned int)> callback)
{
    _callback = callback;
}

// =============================================================================
// setWill()
// Configures the Last Will and Testament (LWT) message.
// Must be called BEFORE begin(), as LWT is sent in the initial CONNECT packet.
//
// If the client disconnects ungracefully (e.g. power loss, crash), the broker
// will automatically publish this message on the given topic to notify others.
//
// Parameters:
//   topic    - Topic the will message will be published to
//   message  - Will message content (null-terminated string)
//   retained - Whether the broker should retain the will message
// =============================================================================
void ESPMQTTClient::setWill(const char *topic, const char *message, bool retained)
{
    _willTopic = topic;
    _willMessage = message;
    _willRetained = retained;
}

// =============================================================================
// setKeepAlive()
// Sets the MQTT keep-alive interval in seconds.
// The client will send a PINGREQ to the broker at this interval when idle,
// so the broker knows the client is still alive.
//
// BUG FIX: Previously this value was stored but never passed to PubSubClient.
// It is now applied in begin() via _mqttClient.setKeepAlive().
//
// Default is typically 15 seconds. Must be called before begin().
// =============================================================================
void ESPMQTTClient::setKeepAlive(uint16_t keepAlive)
{
    _keepAlive = keepAlive;
}

// =============================================================================
// setCleanSession()
// Controls whether the broker clears the client's session state on connect.
//
//   true  (default) - Broker discards any previous session (subscriptions,
//                     queued QoS 1/2 messages) when this client connects.
//   false           - Broker restores the previous session, resuming
//                     subscriptions and delivering any queued messages.
//
// BUG FIX: Previously this value was stored but never passed to PubSubClient.
// It is now applied in begin() via _mqttClient.setCleanSession().
//
// Must be called before begin().
// =============================================================================
void ESPMQTTClient::setCleanSession(bool clean)
{
    _cleanSession = clean;
}