#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "mqtt_client.h"

/* ─────────────────────────────────────────────────────
 *  Configuration structures
 * ───────────────────────────────────────────────────── */

/** WiFi connection configuration */
typedef struct {
    const char *ssid;           /**< WiFi SSID */
    const char *password;       /**< WiFi password */
    uint32_t    timeout_ms;     /**< Connection timeout in milliseconds (0 = default 10 s) */
} mqtt_wifi_config_t;

/** TLS/SSL configuration (optional) */
typedef struct {
    const char *ca_cert;        /**< PEM-encoded CA certificate (NULL = no TLS) */
    const char *client_cert;    /**< PEM-encoded client certificate (NULL = no mTLS) */
    const char *client_key;     /**< PEM-encoded client private key (NULL = no mTLS) */
    bool        skip_cert_verify; /**< Skip server cert verification (INSECURE) */
} mqtt_tls_config_t;

/** MQTT broker configuration */
typedef struct {
    const char        *broker_uri;    /**< e.g. "mqtt://broker.hivemq.com:1883" or "mqtts://..." */
    const char        *client_id;     /**< Unique client identifier (NULL = auto-generated) */
    const char        *username;      /**< Broker username (NULL = anonymous) */
    const char        *password;      /**< Broker password */
    uint16_t           keepalive_sec; /**< Keep-alive interval in seconds (0 = default 60) */
    mqtt_tls_config_t *tls;          /**< TLS config (NULL = plain TCP) */

    /* Last Will and Testament */
    const char *lwt_topic;           /**< LWT topic  (NULL = disabled) */
    const char *lwt_message;         /**< LWT payload */
    int         lwt_qos;             /**< LWT QoS (0/1/2) */
    int         lwt_retain;          /**< LWT retain flag */
} mqtt_broker_config_t;

/* ─────────────────────────────────────────────────────
 *  Callback / event types
 * ───────────────────────────────────────────────────── */

/** Events raised by the library */
typedef enum {
    MQTT_LIB_EVT_CONNECTED,       /**< Connected to broker */
    MQTT_LIB_EVT_DISCONNECTED,    /**< Disconnected from broker */
    MQTT_LIB_EVT_SUBSCRIBED,      /**< Subscription confirmed */
    MQTT_LIB_EVT_UNSUBSCRIBED,    /**< Unsubscription confirmed */
    MQTT_LIB_EVT_PUBLISHED,       /**< Publish confirmed (QoS > 0) */
    MQTT_LIB_EVT_DATA,            /**< Incoming message received */
    MQTT_LIB_EVT_ERROR,           /**< Protocol / transport error */
    MQTT_LIB_EVT_WIFI_CONNECTED,  /**< WiFi link up */
    MQTT_LIB_EVT_WIFI_DISCONNECTED/**< WiFi link down */
} mqtt_lib_event_t;

/** Data delivered with MQTT_LIB_EVT_DATA */
typedef struct {
    char    *topic;       /**< Topic string (null-terminated) */
    int      topic_len;
    char    *payload;     /**< Raw payload (NOT null-terminated) */
    int      payload_len;
    int      qos;
    bool     retain;
    int      msg_id;
} mqtt_message_t;

/**
 * @brief User callback invoked on every library event.
 *
 * @param event   Event type
 * @param message Populated only for MQTT_LIB_EVT_DATA, NULL otherwise
 * @param user_ctx Opaque pointer supplied at init
 */
typedef void (*mqtt_event_callback_t)(mqtt_lib_event_t event,
                                      const mqtt_message_t *message,
                                      void *user_ctx);

/* ─────────────────────────────────────────────────────
 *  Handle
 * ───────────────────────────────────────────────────── */

typedef struct mqtt_lib_handle_s *mqtt_lib_handle_t;

/* ─────────────────────────────────────────────────────
 *  Public API
 * ───────────────────────────────────────────────────── */

/**
 * @brief  Initialise the library, connect to WiFi, then connect to the broker.
 *
 * Call once at startup. Blocks until WiFi is obtained or times out.
 *
 * @param wifi    WiFi credentials
 * @param broker  Broker settings
 * @param cb      Event callback (required)
 * @param user_ctx Opaque pointer forwarded to every callback invocation
 * @param[out] out_handle  Library handle used in subsequent calls
 * @return ESP_OK on success
 */
esp_err_t mqtt_lib_init(const mqtt_wifi_config_t   *wifi,
                         const mqtt_broker_config_t *broker,
                         mqtt_event_callback_t       cb,
                         void                       *user_ctx,
                         mqtt_lib_handle_t          *out_handle);

/**
 * @brief  Publish a message.
 *
 * @param handle   Library handle
 * @param topic    MQTT topic
 * @param payload  Message payload (may contain binary data)
 * @param len      Payload length in bytes (-1 → use strlen)
 * @param qos      Quality of service (0, 1, or 2)
 * @param retain   Retain flag
 * @return message ID (≥ 0) on success, -1 on failure
 */
int mqtt_lib_publish(mqtt_lib_handle_t handle,
                     const char       *topic,
                     const char       *payload,
                     int               len,
                     int               qos,
                     int               retain);

/**
 * @brief  Subscribe to a topic.
 *
 * @param handle  Library handle
 * @param topic   Topic filter (supports wildcards + and #)
 * @param qos     Maximum QoS for delivered messages
 * @return message ID on success, -1 on failure
 */
int mqtt_lib_subscribe(mqtt_lib_handle_t handle,
                       const char       *topic,
                       int               qos);

/**
 * @brief  Unsubscribe from a topic.
 *
 * @param handle  Library handle
 * @param topic   Topic filter previously subscribed
 * @return message ID on success, -1 on failure
 */
int mqtt_lib_unsubscribe(mqtt_lib_handle_t handle, const char *topic);

/**
 * @brief  Query connection state.
 *
 * @param handle  Library handle
 * @return true if currently connected to the broker
 */
bool mqtt_lib_is_connected(mqtt_lib_handle_t handle);

/**
 * @brief  Disconnect from broker and free resources.
 *
 * @param handle  Library handle (invalidated after this call)
 * @return ESP_OK on success
 */
esp_err_t mqtt_lib_deinit(mqtt_lib_handle_t handle);

#ifdef __cplusplus
}
#endif
