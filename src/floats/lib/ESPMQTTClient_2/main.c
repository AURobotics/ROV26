/**
 * @file  main.c
 * @brief Basic MQTT example using esp_mqtt_lib.
 *
 * - Connects to WiFi
 * - Connects to a public HiveMQ broker (no auth, plain TCP)
 * - Subscribes to "esp32/rx"
 * - Publishes "Hello from ESP32!" to "esp32/tx" every 5 seconds
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_mqtt_lib.h"

/* ─── user configuration ────────────────────────────── */
#define WIFI_SSID      "YOUR_WIFI_SSID"
#define WIFI_PASS      "YOUR_WIFI_PASSWORD"
#define BROKER_URI     "mqtt://broker.hivemq.com:1883"
#define PUB_TOPIC      "esp32/tx"
#define SUB_TOPIC      "esp32/rx"
#define PUBLISH_PERIOD_MS  5000

static const char *TAG = "EXAMPLE";

/* ─── library handle ─────────────────────────────────── */
static mqtt_lib_handle_t g_handle = NULL;

/* ═══════════════════════════════════════════════════════
 *  Event callback
 * ═══════════════════════════════════════════════════════ */
static void on_mqtt_event(mqtt_lib_event_t         event,
                          const mqtt_message_t     *msg,
                          void                     *user_ctx)
{
    switch (event) {
    case MQTT_LIB_EVT_WIFI_CONNECTED:
        ESP_LOGI(TAG, "[EVENT] WiFi connected");
        break;

    case MQTT_LIB_EVT_WIFI_DISCONNECTED:
        ESP_LOGW(TAG, "[EVENT] WiFi disconnected");
        break;

    case MQTT_LIB_EVT_CONNECTED:
        ESP_LOGI(TAG, "[EVENT] MQTT broker connected");
        /* Subscribe once we are connected */
        mqtt_lib_subscribe(g_handle, SUB_TOPIC, 1);
        break;

    case MQTT_LIB_EVT_DISCONNECTED:
        ESP_LOGW(TAG, "[EVENT] MQTT broker disconnected");
        break;

    case MQTT_LIB_EVT_SUBSCRIBED:
        ESP_LOGI(TAG, "[EVENT] Subscribed to " SUB_TOPIC);
        break;

    case MQTT_LIB_EVT_PUBLISHED:
        ESP_LOGI(TAG, "[EVENT] Publish acknowledged");
        break;

    case MQTT_LIB_EVT_DATA:
        /* msg is guaranteed non-NULL here */
        ESP_LOGI(TAG, "[EVENT] Incoming message on '%.*s': %.*s",
                 msg->topic_len,   msg->topic,
                 msg->payload_len, msg->payload);
        break;

    case MQTT_LIB_EVT_ERROR:
        ESP_LOGE(TAG, "[EVENT] MQTT error");
        break;

    default:
        break;
    }
}

/* ═══════════════════════════════════════════════════════
 *  Publish task
 * ═══════════════════════════════════════════════════════ */
static void publish_task(void *pvParam)
{
    uint32_t count = 0;
    char     buf[64];

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(PUBLISH_PERIOD_MS));

        if (!mqtt_lib_is_connected(g_handle)) {
            ESP_LOGW(TAG, "Not connected, skipping publish");
            continue;
        }

        snprintf(buf, sizeof(buf), "Hello from ESP32! (msg #%lu)", (unsigned long)++count);
        int id = mqtt_lib_publish(g_handle, PUB_TOPIC, buf, -1, 1, 0);
        if (id >= 0)
            ESP_LOGI(TAG, "Published: %s  (msg_id=%d)", buf, id);
    }
}

/* ═══════════════════════════════════════════════════════
 *  app_main
 * ═══════════════════════════════════════════════════════ */
void app_main(void)
{
    ESP_LOGI(TAG, "Starting MQTT example…");

    mqtt_wifi_config_t wifi_cfg = {
        .ssid       = WIFI_SSID,
        .password   = WIFI_PASS,
        .timeout_ms = 15000,
    };

    mqtt_broker_config_t broker_cfg = {
        .broker_uri    = BROKER_URI,
        .client_id     = "esp32_example_001",   /* must be unique on the broker */
        .keepalive_sec = 60,
        /* No authentication, no TLS, no LWT for this simple example */
    };

    esp_err_t err = mqtt_lib_init(&wifi_cfg, &broker_cfg,
                                  on_mqtt_event, NULL, &g_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "mqtt_lib_init failed: %s", esp_err_to_name(err));
        return;
    }

    /* Spawn publisher */
    xTaskCreate(publish_task, "pub_task", 4096, NULL, 5, NULL);
}
