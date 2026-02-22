/**
 * @file  esp_mqtt_lib.c
 * @brief ESP-IDF MQTT client library implementation.
 *
 * Uses:
 *   - esp_wifi   – WiFi driver
 *   - esp_event  – system / IP event loop
 *   - mqtt_client – ESP-IDF MQTT client
 */

#include "esp_mqtt_lib.h"

#include <string.h>
#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "mqtt_client.h"

/* ─── logging ──────────────────────────────────────── */
static const char *TAG = "ESP_MQTT_LIB";

/* ─── event group bits ─────────────────────────────── */
#define WIFI_CONNECTED_BIT   BIT0
#define WIFI_FAIL_BIT        BIT1

/* ─── default values ───────────────────────────────── */
#define DEFAULT_WIFI_TIMEOUT_MS   10000
#define DEFAULT_KEEPALIVE_SEC     60
#define WIFI_MAX_RETRY            5

/* ─── internal handle ──────────────────────────────── */
struct mqtt_lib_handle_s {
    esp_mqtt_client_handle_t   mqtt_client;
    mqtt_event_callback_t      user_cb;
    void                      *user_ctx;
    bool                       connected;
    EventGroupHandle_t         wifi_eg;
    int                        wifi_retry;
};

/* ═══════════════════════════════════════════════════════
 *  WiFi event handler
 * ═══════════════════════════════════════════════════════ */
static void wifi_event_handler(void *arg, esp_event_base_t base,
                               int32_t id, void *data)
{
    mqtt_lib_handle_t h = (mqtt_lib_handle_t)arg;

    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();

    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        if (h->wifi_retry < WIFI_MAX_RETRY) {
            esp_wifi_connect();
            h->wifi_retry++;
            ESP_LOGW(TAG, "WiFi reconnect attempt %d/%d", h->wifi_retry, WIFI_MAX_RETRY);
        } else {
            xEventGroupSetBits(h->wifi_eg, WIFI_FAIL_BIT);
            ESP_LOGE(TAG, "WiFi failed after %d retries", WIFI_MAX_RETRY);
        }
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_WIFI_DISCONNECTED, NULL, h->user_ctx);

    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *ev = (ip_event_got_ip_t *)data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&ev->ip_info.ip));
        h->wifi_retry = 0;
        xEventGroupSetBits(h->wifi_eg, WIFI_CONNECTED_BIT);
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_WIFI_CONNECTED, NULL, h->user_ctx);
    }
}

/* ═══════════════════════════════════════════════════════
 *  MQTT event handler
 * ═══════════════════════════════════════════════════════ */
static void mqtt_event_handler(void *arg, esp_event_base_t base,
                               int32_t id, void *data)
{
    mqtt_lib_handle_t       h   = (mqtt_lib_handle_t)arg;
    esp_mqtt_event_handle_t evt = (esp_mqtt_event_handle_t)data;

    switch ((esp_mqtt_event_id_t)id) {

    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT connected");
        h->connected = true;
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_CONNECTED, NULL, h->user_ctx);
        break;

    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "MQTT disconnected");
        h->connected = false;
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_DISCONNECTED, NULL, h->user_ctx);
        break;

    case MQTT_EVENT_SUBSCRIBED:
        ESP_LOGI(TAG, "MQTT subscribed, msg_id=%d", evt->msg_id);
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_SUBSCRIBED, NULL, h->user_ctx);
        break;

    case MQTT_EVENT_UNSUBSCRIBED:
        ESP_LOGI(TAG, "MQTT unsubscribed, msg_id=%d", evt->msg_id);
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_UNSUBSCRIBED, NULL, h->user_ctx);
        break;

    case MQTT_EVENT_PUBLISHED:
        ESP_LOGI(TAG, "MQTT published, msg_id=%d", evt->msg_id);
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_PUBLISHED, NULL, h->user_ctx);
        break;

    case MQTT_EVENT_DATA: {
        ESP_LOGI(TAG, "MQTT data: topic=%.*s (%d bytes)",
                 evt->topic_len, evt->topic, evt->data_len);

        mqtt_message_t msg = {
            .topic       = evt->topic,
            .topic_len   = evt->topic_len,
            .payload     = evt->data,
            .payload_len = evt->data_len,
            .qos         = evt->qos,
            .retain      = evt->retain,
            .msg_id      = evt->msg_id,
        };
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_DATA, &msg, h->user_ctx);
        break;
    }

    case MQTT_EVENT_ERROR:
        ESP_LOGE(TAG, "MQTT error type: %d", evt->error_handle->error_type);
        if (evt->error_handle->error_type == MQTT_ERROR_TYPE_TCP_TRANSPORT) {
            ESP_LOGE(TAG, "  errno: %d", evt->error_handle->esp_transport_sock_errno);
        }
        if (h->user_cb)
            h->user_cb(MQTT_LIB_EVT_ERROR, NULL, h->user_ctx);
        break;

    default:
        ESP_LOGD(TAG, "Unhandled MQTT event id: %d", (int)id);
        break;
    }
}

/* ═══════════════════════════════════════════════════════
 *  Internal helpers
 * ═══════════════════════════════════════════════════════ */

static esp_err_t wifi_init_sta(const mqtt_wifi_config_t *cfg,
                               mqtt_lib_handle_t         h)
{
    /* Initialise NVS (required by WiFi driver) */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t init_cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init_cfg));

    /* Register event handlers */
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, h, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event_handler, h, NULL));

    wifi_config_t wifi_cfg = { 0 };
    strlcpy((char *)wifi_cfg.sta.ssid,     cfg->ssid,     sizeof(wifi_cfg.sta.ssid));
    strlcpy((char *)wifi_cfg.sta.password, cfg->password, sizeof(wifi_cfg.sta.password));
    wifi_cfg.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
    wifi_cfg.sta.pmf_cfg.capable    = true;
    wifi_cfg.sta.pmf_cfg.required   = false;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "WiFi STA started, connecting to '%s'…", cfg->ssid);

    uint32_t timeout = cfg->timeout_ms ? cfg->timeout_ms : DEFAULT_WIFI_TIMEOUT_MS;
    EventBits_t bits = xEventGroupWaitBits(h->wifi_eg,
                                           WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
                                           pdFALSE, pdFALSE,
                                           pdMS_TO_TICKS(timeout));

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "WiFi connected");
        return ESP_OK;
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGE(TAG, "WiFi connection failed");
        return ESP_FAIL;
    } else {
        ESP_LOGE(TAG, "WiFi connection timed out");
        return ESP_ERR_TIMEOUT;
    }
}

static esp_err_t mqtt_start(const mqtt_broker_config_t *broker,
                            mqtt_lib_handle_t            h)
{
    esp_mqtt_client_config_t cfg = { 0 };

    /* Broker URI */
    cfg.broker.address.uri = broker->broker_uri;

    /* Credentials */
    if (broker->username)  cfg.credentials.username  = broker->username;
    if (broker->password)  cfg.credentials.authentication.password = broker->password;
    if (broker->client_id) cfg.credentials.client_id = broker->client_id;

    /* Keep-alive */
    cfg.session.keepalive = broker->keepalive_sec ? broker->keepalive_sec
                                                   : DEFAULT_KEEPALIVE_SEC;

    /* TLS */
    if (broker->tls) {
        if (broker->tls->ca_cert) {
            cfg.broker.verification.certificate     = broker->tls->ca_cert;
        }
        if (broker->tls->client_cert) {
            cfg.credentials.authentication.certificate = broker->tls->client_cert;
        }
        if (broker->tls->client_key) {
            cfg.credentials.authentication.key        = broker->tls->client_key;
        }
        cfg.broker.verification.skip_cert_common_name_check = broker->tls->skip_cert_verify;
    }

    /* Last Will and Testament */
    if (broker->lwt_topic) {
        cfg.session.last_will.topic   = broker->lwt_topic;
        cfg.session.last_will.msg     = broker->lwt_message;
        cfg.session.last_will.msg_len = broker->lwt_message
                                            ? (int)strlen(broker->lwt_message) : 0;
        cfg.session.last_will.qos     = broker->lwt_qos;
        cfg.session.last_will.retain  = broker->lwt_retain;
    }

    h->mqtt_client = esp_mqtt_client_init(&cfg);
    if (!h->mqtt_client) {
        ESP_LOGE(TAG, "Failed to create MQTT client");
        return ESP_FAIL;
    }

    ESP_ERROR_CHECK(esp_mqtt_client_register_event(
        h->mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, h));

    return esp_mqtt_client_start(h->mqtt_client);
}

/* ═══════════════════════════════════════════════════════
 *  Public API
 * ═══════════════════════════════════════════════════════ */

esp_err_t mqtt_lib_init(const mqtt_wifi_config_t   *wifi,
                         const mqtt_broker_config_t *broker,
                         mqtt_event_callback_t       cb,
                         void                       *user_ctx,
                         mqtt_lib_handle_t          *out_handle)
{
    if (!wifi || !broker || !cb || !out_handle) return ESP_ERR_INVALID_ARG;

    mqtt_lib_handle_t h = calloc(1, sizeof(struct mqtt_lib_handle_s));
    if (!h) return ESP_ERR_NO_MEM;

    h->user_cb   = cb;
    h->user_ctx  = user_ctx;
    h->wifi_eg   = xEventGroupCreate();

    esp_err_t err = wifi_init_sta(wifi, h);
    if (err != ESP_OK) {
        vEventGroupDelete(h->wifi_eg);
        free(h);
        return err;
    }

    err = mqtt_start(broker, h);
    if (err != ESP_OK) {
        vEventGroupDelete(h->wifi_eg);
        free(h);
        return err;
    }

    *out_handle = h;
    ESP_LOGI(TAG, "Library initialised");
    return ESP_OK;
}

int mqtt_lib_publish(mqtt_lib_handle_t handle,
                     const char       *topic,
                     const char       *payload,
                     int               len,
                     int               qos,
                     int               retain)
{
    if (!handle || !topic) return -1;
    if (len < 0) len = payload ? (int)strlen(payload) : 0;

    int msg_id = esp_mqtt_client_publish(handle->mqtt_client,
                                         topic, payload, len, qos, retain);
    if (msg_id < 0)
        ESP_LOGE(TAG, "Publish failed for topic '%s'", topic);
    else
        ESP_LOGD(TAG, "Published to '%s', msg_id=%d", topic, msg_id);

    return msg_id;
}

int mqtt_lib_subscribe(mqtt_lib_handle_t handle, const char *topic, int qos)
{
    if (!handle || !topic) return -1;

    int msg_id = esp_mqtt_client_subscribe(handle->mqtt_client, topic, qos);
    if (msg_id < 0)
        ESP_LOGE(TAG, "Subscribe failed for topic '%s'", topic);
    else
        ESP_LOGI(TAG, "Subscribed to '%s' (QoS %d), msg_id=%d", topic, qos, msg_id);

    return msg_id;
}

int mqtt_lib_unsubscribe(mqtt_lib_handle_t handle, const char *topic)
{
    if (!handle || !topic) return -1;

    int msg_id = esp_mqtt_client_unsubscribe(handle->mqtt_client, topic);
    if (msg_id < 0)
        ESP_LOGE(TAG, "Unsubscribe failed for topic '%s'", topic);
    else
        ESP_LOGI(TAG, "Unsubscribed from '%s', msg_id=%d", topic, msg_id);

    return msg_id;
}

bool mqtt_lib_is_connected(mqtt_lib_handle_t handle)
{
    return handle ? handle->connected : false;
}

esp_err_t mqtt_lib_deinit(mqtt_lib_handle_t handle)
{
    if (!handle) return ESP_ERR_INVALID_ARG;

    if (handle->mqtt_client) {
        esp_mqtt_client_stop(handle->mqtt_client);
        esp_mqtt_client_destroy(handle->mqtt_client);
    }

    vEventGroupDelete(handle->wifi_eg);
    free(handle);
    ESP_LOGI(TAG, "Library de-initialised");
    return ESP_OK;
}
