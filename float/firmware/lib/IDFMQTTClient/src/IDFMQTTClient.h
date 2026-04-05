#pragma once

#include <string>
#include <functional>
#include <map>
#include "mqtt_client.h"
#include "esp_err.h"

/**
 * @brief MQTT connection configuration
 */
struct MQTTConfig
{
    std::string broker_uri; // in the form: mqtt://<host>:<port> or mqtts://<host>:<port>
    std::string client_id;
    std::string username;
    std::string password;

    // TLS (optional)
    const char *cert_pem = nullptr;    ///< Server certificate (PEM) for TLS
    const char *client_cert = nullptr; ///< Client certificate (PEM) for mutual TLS
    const char *client_key = nullptr;  ///< Client private key (PEM) for mutual TLS

    // Keep-alive / reconnect
    int keepalive_sec = 120;
    bool disable_auto_reconnect = false;

    // Last-will
    std::string lwt_topic;
    std::string lwt_message;
    int lwt_qos = 0;
    bool lwt_retain = false;
};

/**
 * @brief Lightweight wrapper around the ESP-IDF esp_mqtt_client.
 *
 * Usage:
 *   IDFMQTTClient mgr;
 *   mgr.setOnConnected([]{ mgr.subscribe("my/topic"); });
 *   mgr.setOnMessage([](const std::string& topic, const std::string& payload){ … });
 *   mgr.begin(config);
 */
class IDFMQTTClient
{
public:
    // Callback types
    using ConnectedCb = std::function<void()>;
    using DisconnectedCb = std::function<void()>;
    using MessageCb = std::function<void(const std::string &topic,
                                         const std::string &payload)>;
    using PublishedCb = std::function<void(int msg_id)>;
    using ErrorCb = std::function<void(esp_mqtt_error_codes_t *error)>;

    IDFMQTTClient();
    ~IDFMQTTClient();

    // Non-copyable
    IDFMQTTClient(const IDFMQTTClient &) = delete;
    IDFMQTTClient &operator=(const IDFMQTTClient &) = delete;

    // Lifecycle

    /**
     * @brief Initialise and start the MQTT client.
     * @return ESP_OK on success.
     */
    esp_err_t begin(const MQTTConfig &config);

    /**
     * @brief Stop the client and free resources.
     */
    void end();

    /**
     * @brief Returns true after a successful MQTT_EVENT_CONNECTED.
     */
    bool isConnected() const { return connected_; }

    // Publish

    /**
     * @brief Publish a message.
     * @param topic   MQTT topic string.
     * @param payload Message payload (binary-safe).
     * @param qos     0, 1, or 2.
     * @param retain  Retain flag.
     * @return Message ID (≥0) on success, -1 on failure.
     */
    int publish(const std::string &topic,
                const std::string &payload,
                int qos = 0,
                bool retain = false);

    int publish(const std::string &topic,
                const uint8_t *data,
                size_t len,
                int qos = 0,
                bool retain = false);

    /**
     * @brief send file in chunks over MQTT.
     *
     * This is necessary because MQTT has a maximum payload size.
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
     * @param path Path to the file to send
     * @param qos MQTT QoS level for the messages
     * @param retain Whether the MQTT messages should be retained
     *
     * @return true if file sent successfully, false otherwise
     */
    bool publishFileChunkedOverTopics(const std::string &topic,
                                      const char *path,
                                      int qos = 0,
                                      bool retain = false);

    // Subscribe / Unsubscribe

    /**
     * @brief Subscribe to a topic (wildcards supported).
     * @return Message ID on success, -1 on failure.
     */
    int subscribe(const std::string &topic, int qos = 0);

    /**
     * @brief Unsubscribe from a topic.
     * @return Message ID on success, -1 on failure.
     */
    int unsubscribe(const std::string &topic);

    // Callbacks

    void setOnConnected(ConnectedCb cb) { onConnected_ = std::move(cb); }
    void setOnDisconnected(DisconnectedCb cb) { onDisconnected_ = std::move(cb); }
    void setOnMessage(MessageCb cb) { onMessage_ = std::move(cb); }
    void setOnPublished(PublishedCb cb) { onPublished_ = std::move(cb); }
    void setOnError(ErrorCb cb) { onError_ = std::move(cb); }

    // Raw handle (advanced use)
    esp_mqtt_client_handle_t handle() const { return client_; }

    // subscribtion list
    std::map<std::string, int> getSubscribedTopics() const
    {
        std::map<std::string, int> copy;
        xSemaphoreTake(topics_mutex_, portMAX_DELAY);
        copy = _subscribed_topics;
        xSemaphoreGive(topics_mutex_);
        return copy;
    }

private:
    SemaphoreHandle_t topics_mutex_ = nullptr; // mutex to protect _subscribed_topics
    static void eventHandler(void *handler_args,
                             esp_event_base_t base,
                             int32_t event_id,
                             void *event_data);

    void dispatchEvent(esp_mqtt_event_handle_t event);

    esp_mqtt_client_handle_t client_ = nullptr;
    bool connected_ = false;

    // track subscribed topics and their QoS for re-subscription on reconnect and deletes list on disconnect
    std::map<std::string, int> _subscribed_topics; // for tracking subscriptions
    void reSubscribe();

    ConnectedCb onConnected_;
    DisconnectedCb onDisconnected_;
    MessageCb onMessage_;
    PublishedCb onPublished_;
    ErrorCb onError_;
};
