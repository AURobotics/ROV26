#include "IDFMQTTClient.h"

#include <cstring>
#include "esp_log.h"
#include "mbedtls/base64.h"
#include "cJSON.h"

static const char *TAG = "IDFMQTTClient";

IDFMQTTClient::IDFMQTTClient() = default;

IDFMQTTClient::~IDFMQTTClient()
{
    end();
}

// Setup ########################################################################

// No need to call any thing in loop, the IDF MQTT client runs in the background (RTOS task) and uses callbacks for events.
esp_err_t IDFMQTTClient::begin(const MQTTConfig &cfg)
{
    // Only create mutex if it doesn't already exist
    if (!topics_mutex_)
    {
        topics_mutex_ = xSemaphoreCreateMutex();
        if (!topics_mutex_)
        {
            ESP_LOGE(TAG, "Failed to create topics mutex");
            return ESP_FAIL;
        }
    }

    if (client_)
    {
        ESP_LOGW(TAG, "begin() called while already initialised — ignoring");
        return ESP_ERR_INVALID_STATE;
    }

    // Build the IDF config struct
    esp_mqtt_client_config_t mqtt_cfg = {};

    mqtt_cfg.broker.address.uri = cfg.broker_uri.c_str();
    mqtt_cfg.credentials.client_id = cfg.client_id.empty() ? nullptr : cfg.client_id.c_str();
    mqtt_cfg.credentials.username = cfg.username.empty() ? nullptr : cfg.username.c_str();
    mqtt_cfg.credentials.authentication.password = cfg.password.empty() ? nullptr : cfg.password.c_str();

    mqtt_cfg.session.keepalive = cfg.keepalive_sec;
    mqtt_cfg.network.disable_auto_reconnect = cfg.disable_auto_reconnect;

    mqtt_cfg.network.timeout_ms = 10000;

    // if TLS is enabled
    if (cfg.cert_pem)
    {
        mqtt_cfg.broker.verification.certificate = cfg.cert_pem;
    }
    if (cfg.client_cert)
    {
        mqtt_cfg.credentials.authentication.certificate = cfg.client_cert;
    }
    if (cfg.client_key)
    {
        mqtt_cfg.credentials.authentication.key = cfg.client_key;
    }

    // if Last-will
    if (!cfg.lwt_topic.empty())
    {
        mqtt_cfg.session.last_will.topic = cfg.lwt_topic.c_str();
        mqtt_cfg.session.last_will.msg = cfg.lwt_message.c_str();
        mqtt_cfg.session.last_will.msg_len = static_cast<int>(cfg.lwt_message.size());
        mqtt_cfg.session.last_will.qos = cfg.lwt_qos;
        mqtt_cfg.session.last_will.retain = cfg.lwt_retain ? 1 : 0;
    }

    // Create client
    client_ = esp_mqtt_client_init(&mqtt_cfg);
    if (!client_)
    {
        ESP_LOGE(TAG, "esp_mqtt_client_init failed");
        return ESP_FAIL;
    }

    // Register event handler
    esp_err_t err = esp_mqtt_client_register_event(
        client_,
        static_cast<esp_mqtt_event_id_t>(ESP_EVENT_ANY_ID),
        eventHandler,
        this);

    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "register_event failed: %s", esp_err_to_name(err));
        esp_mqtt_client_destroy(client_);
        client_ = nullptr;
        return err;
    }

    // Start client
    err = esp_mqtt_client_start(client_);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "esp_mqtt_client_start failed: %s", esp_err_to_name(err));
        esp_mqtt_client_destroy(client_);
        client_ = nullptr;
        return err;
    }

    ESP_LOGI(TAG, "MQTT client started -> %s", cfg.broker_uri.c_str());
    return ESP_OK;
}

void IDFMQTTClient::end()
{
    if (!client_)
        return;

    xSemaphoreTake(topics_mutex_, portMAX_DELAY);
    _subscribed_topics.clear(); // Clear subscribed topics on disconnect
    xSemaphoreGive(topics_mutex_);

    if (topics_mutex_)
    {
        vSemaphoreDelete(topics_mutex_);
        topics_mutex_ = nullptr;
    }

    esp_mqtt_client_stop(client_);
    esp_mqtt_client_destroy(client_);
    client_ = nullptr;
    connected_ = false;
    ESP_LOGI(TAG, "MQTT client stopped");
}

// Publish ########################################################################

int IDFMQTTClient::publish(const std::string &topic,
                           const std::string &payload,
                           int qos,
                           bool retain)
{
    return publish(topic,
                   reinterpret_cast<const uint8_t *>(payload.data()),
                   payload.size(),
                   qos,
                   retain);
}

int IDFMQTTClient::publish(const std::string &topic,
                           const uint8_t *data,
                           size_t len,
                           int qos,
                           bool retain)
{
    if (!client_ || !connected_)
    {
        ESP_LOGW(TAG, "publish() called while not connected");
        return -1;
    }

    int msg_id = esp_mqtt_client_publish(
        client_,
        topic.c_str(),
        reinterpret_cast<const char *>(data),
        static_cast<int>(len),
        qos,
        retain ? 1 : 0);

    if (msg_id < 0)
    {
        ESP_LOGE(TAG, "publish failed on topic '%s'", topic.c_str());
    }
    else
    {
        ESP_LOGD(TAG, "publish -> topic='%s' len=%zu qos=%d msg_id=%d",
                 topic.c_str(), len, qos, msg_id);
    }
    return msg_id;
}

bool IDFMQTTClient::publishFileChunkedOverTopics(const std::string &topic,
                                                 const char *path,
                                                 const char *name,
                                                 int qos,
                                                 bool retain)
{
    if (!client_ || !connected_)
    {
        ESP_LOGW(TAG, "publishFileChunkedOverTopics() called while not connected");
        return false;
    }

    FILE *f = fopen(path, "rb");
    if (!f)
    {
        ESP_LOGE(TAG, "Failed to open file: %s", path);
        return false;
    }

    fseek(f, 0, SEEK_END);
    size_t fileSize = ftell(f);
    fseek(f, 0, SEEK_SET);

    ESP_LOGI(TAG, "Publishing file: %s | Size: %zu bytes", path, fileSize);

    // Calculate chunks
    // originally 180 bytes -> 240 bytes in base64; but that failed
    // so decreased to 150 bytes -> 200 bytes in base64, which works reliably
    static constexpr int RAW_CHUNK_SIZE = 150;

    int totalChunks = (fileSize + RAW_CHUNK_SIZE - 1) / RAW_CHUNK_SIZE; // ceiling division

    ESP_LOGI(TAG, "File will be sent in %d chunks + metadata", totalChunks);

    // Send file metadata first
    // - filename: name of file
    // - size: total bytes
    // - chunks: number of chunks
    // - encoding: how the data is encoded (base64 in this case)

    char metaTopic[128];
    snprintf(metaTopic, sizeof(metaTopic), "%s/meta", topic.c_str());

    cJSON *meta = cJSON_CreateObject();
    cJSON_AddStringToObject(meta, "filename", name);
    cJSON_AddNumberToObject(meta, "size", fileSize);
    cJSON_AddNumberToObject(meta, "chunks", totalChunks);
    cJSON_AddStringToObject(meta, "encoding", "base64");

    char *metaStr = cJSON_PrintUnformatted(meta);

    ESP_LOGI(TAG, "Sending metadata on topic '%s': %s", metaTopic, metaStr);

    if (publish(metaTopic, metaStr, qos, false) == -1)
    {
        ESP_LOGE(TAG, "Failed to send metadata");
        fclose(f);
        return false;
    }

    cJSON_free(metaStr);
    cJSON_Delete(meta);

    vTaskDelay(pdMS_TO_TICKS(50)); // Small delay to let receiver process metadata

    // buffer for reading file
    uint8_t buffer[RAW_CHUNK_SIZE]; // Raw file data buffer
    int bytesRead;
    bool success = true;

    // Send each chunk
    int outBufSize = ((RAW_CHUNK_SIZE + 2) / 3) * 4 + 1; // Base64 encoded buffer size
    unsigned char* encodedData = (unsigned char*) malloc(outBufSize); // Base64 encoded buffer
    for (int chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++)
    {
        if (!connected_)
        {
            ESP_LOGE(TAG, "Lost connection at chunk %d/%d", chunkIndex, totalChunks);
            free(encodedData);
            fclose(f);
            return false;
        }

        // Read a chunk from the file
        bytesRead = fread(buffer, 1, RAW_CHUNK_SIZE, f);

        if (bytesRead <= 0)
        {
            ESP_LOGE(TAG, "Unexpected end of file at chunk %d", chunkIndex);
            success = false;
            break;
        }

        // encode the binary chunk to base64
        size_t outLen = 0;
        mbedtls_base64_encode(encodedData, outBufSize, &outLen, buffer, bytesRead);

        // chunk-specific topic
        // format: base_topic/chunk/chunk_number
        // e.g. "float/data/chunk/0", "float/data/chunk/1", etc.
        char chunkTopic[128];
        snprintf(chunkTopic, sizeof(chunkTopic), "%s/chunk/%d", topic.c_str(), chunkIndex);

        // Send the chunk
        // Each chunk contains base64 encoded data
        if (publish(chunkTopic, encodedData, outLen, qos, false) == -1)
        {
            ESP_LOGE(TAG, "Failed to send chunk %d, chunck size: %d", chunkIndex, outLen);
            success = false;
            break;
        }

        // Print progress
        ESP_LOGI(TAG, "Sent chunk %d/%d (raw bytes: %d)", chunkIndex + 1, totalChunks, bytesRead);

        // Small delay between chunks to avoid flooding MQTT broker
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    free(encodedData);

    fclose(f);

    return success;
}

// Subscribe / Unsubscribe ########################################################################

int IDFMQTTClient::subscribe(const std::string &topic, int qos)
{
    if (!client_ || !connected_)
    {
        ESP_LOGW(TAG, "subscribe() called while not connected");
        return -1;
    }

    int msg_id = esp_mqtt_client_subscribe(client_, topic.c_str(), qos);
    if (msg_id < 0)
    {
        ESP_LOGE(TAG, "subscribe failed on topic '%s'", topic.c_str());
    }
    else
    {
        ESP_LOGI(TAG, "subscribed -> '%s' (qos=%d, msg_id=%d)",
                 topic.c_str(), qos, msg_id);
        xSemaphoreTake(topics_mutex_, portMAX_DELAY);
        _subscribed_topics[topic] = qos; // Track the subscribed topic and its QoS
        xSemaphoreGive(topics_mutex_);
    }
    return msg_id;
}

int IDFMQTTClient::unsubscribe(const std::string &topic)
{
    if (!client_)
        return -1;

    int msg_id = esp_mqtt_client_unsubscribe(client_, topic.c_str());
    if (msg_id < 0)
    {
        ESP_LOGE(TAG, "unsubscribe failed on topic '%s'", topic.c_str());
    }
    else
    {
        ESP_LOGI(TAG, "unsubscribed -> '%s' (msg_id=%d)", topic.c_str(), msg_id);
        xSemaphoreTake(topics_mutex_, portMAX_DELAY);
        _subscribed_topics.erase(topic); // Remove topic from tracking map
        xSemaphoreGive(topics_mutex_);
    }
    return msg_id;
}

// Event dispatch ########################################################################

/* static */
void IDFMQTTClient::eventHandler(void *handler_args,
                                 esp_event_base_t /* base */,
                                 int32_t event_id,
                                 void *event_data)
{
    auto *self = static_cast<IDFMQTTClient *>(handler_args);
    auto *event = static_cast<esp_mqtt_event_handle_t>(event_data);
    self->dispatchEvent(event);
    (void)event_id; // covered by event->event_id
}

void IDFMQTTClient::dispatchEvent(esp_mqtt_event_handle_t event)
{
    switch (event->event_id)
    {

    // Connected
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");
        connected_ = true;
        reSubscribe(); // Re-subscribe to all topics on reconnect
        if (onConnected_)
            onConnected_();
        break;

    // Disconnected
    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "MQTT_EVENT_DISCONNECTED");
        connected_ = false;
        if (onDisconnected_)
            onDisconnected_();
        break;

    // Subscribed
    case MQTT_EVENT_SUBSCRIBED:
        ESP_LOGD(TAG, "MQTT_EVENT_SUBSCRIBED msg_id=%d", event->msg_id);
        break;

    // Unsubscribed
    case MQTT_EVENT_UNSUBSCRIBED:
        ESP_LOGD(TAG, "MQTT_EVENT_UNSUBSCRIBED msg_id=%d", event->msg_id);
        break;

    // Published
    case MQTT_EVENT_PUBLISHED:
        ESP_LOGD(TAG, "MQTT_EVENT_PUBLISHED msg_id=%d", event->msg_id);
        if (onPublished_)
            onPublished_(event->msg_id);
        break;

    // Incoming data
    case MQTT_EVENT_DATA:
    {
        // topic_len / data_len may be 0 for fragmented messages;
        // handle only complete single-packet messages for simplicity.
        if (event->topic && event->topic_len > 0)
        {
            std::string topic(event->topic,
                              static_cast<size_t>(event->topic_len));
            std::string payload(event->data,
                                static_cast<size_t>(event->data_len));

            ESP_LOGD(TAG, "MQTT_EVENT_DATA topic='%s' len=%d",
                     topic.c_str(), event->data_len);

            if (onMessage_)
                onMessage_(topic, payload);
        }
        break;
    }

    // Error
    case MQTT_EVENT_ERROR:
        ESP_LOGE(TAG, "MQTT_EVENT_ERROR");
        if (event->error_handle)
        {
            if (event->error_handle->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT)
            {
                ESP_LOGE(TAG, "  esp_tls_last_esp_err  = 0x%x",
                         event->error_handle->esp_tls_last_esp_err);
                ESP_LOGE(TAG, "  esp_tls_stack_err     = 0x%x",
                         event->error_handle->esp_tls_stack_err);
                ESP_LOGE(TAG, "  esp_transport_sock_errno = %d",
                         event->error_handle->esp_transport_sock_errno);
            }
            else if (event->error_handle->error_type ==
                     MQTT_ERROR_TYPE_CONNECTION_REFUSED)
            {
                ESP_LOGE(TAG, "  connection refused, reason = 0x%x",
                         event->error_handle->connect_return_code);
            }
            if (onError_)
                onError_(event->error_handle);
        }
        break;

    // Before connect (useful for dynamic credential refresh)
    case MQTT_EVENT_BEFORE_CONNECT:
        ESP_LOGD(TAG, "MQTT_EVENT_BEFORE_CONNECT");
        break;

    default:
        ESP_LOGD(TAG, "Unhandled MQTT event id=%d", event->event_id);
        break;
    }
}

void IDFMQTTClient::reSubscribe()
{
    if (!connected_ || !client_) return;

    xSemaphoreTake(topics_mutex_, portMAX_DELAY);
    for (const auto &pair : _subscribed_topics)
    {
        const std::string &topic = pair.first;
        int qos = pair.second;
        int msg_id = esp_mqtt_client_subscribe(client_, topic.c_str(), qos);
        if (msg_id < 0)
        {
            ESP_LOGE(TAG, "Failed to re-subscribe to topic '%s'", topic.c_str());
        }
        else
        {
            ESP_LOGI(TAG, "Re-subscribed to topic '%s' with msg_id=%d", topic.c_str(), msg_id);
        }
    }
    xSemaphoreGive(topics_mutex_);
}
