# ESP MQTT Client Library (ESP-IDF / PlatformIO)

A clean, minimal C library for connecting an ESP32 to an MQTT broker over WiFi using the **ESP-IDF native API** (`esp_wifi`, `esp_event`, `mqtt_client`).

---

## Features

| Feature | Details |
|---|---|
| WiFi STA | Auto-reconnect, configurable timeout |
| MQTT | QoS 0/1/2, retain, LWT |
| TLS / mTLS | CA cert, client cert+key, skip-verify option |
| Event callback | Single callback for all events |
| Thread-safe | MQTT client runs in its own FreeRTOS task |

---

## File Structure

```
esp_mqtt_lib/
├── library.json              ← PlatformIO manifest
├── include/
│   └── esp_mqtt_lib.h        ← Public API
├── src/
│   └── esp_mqtt_lib.c        ← Implementation
└── examples/
    └── basic_mqtt/
        ├── platformio.ini
        ├── sdkconfig.defaults
        └── src/
            └── main.c
```

---

## Quick Start

### 1. Add the library to your project

**`platformio.ini`**
```ini
[env:esp32dev]
platform  = espressif32
board     = esp32dev
framework = espidf
lib_deps  =
    ; local path:
    symlink://path/to/esp_mqtt_lib
    ; or GitHub:
    ; https://github.com/yourname/esp-mqtt-client
```

### 2. Include the header

```c
#include "esp_mqtt_lib.h"
```

### 3. Initialise

```c
static mqtt_lib_handle_t mqtt;

static void on_event(mqtt_lib_event_t event,
                     const mqtt_message_t *msg, void *ctx)
{
    if (event == MQTT_LIB_EVT_CONNECTED)
        mqtt_lib_subscribe(mqtt, "my/topic", 1);

    if (event == MQTT_LIB_EVT_DATA)
        printf("Got: %.*s\n", msg->payload_len, msg->payload);
}

void app_main(void) {
    mqtt_wifi_config_t wifi = {
        .ssid = "MySSID", .password = "MyPass"
    };
    mqtt_broker_config_t broker = {
        .broker_uri = "mqtt://broker.hivemq.com:1883",
        .client_id  = "my_esp32"
    };

    mqtt_lib_init(&wifi, &broker, on_event, NULL, &mqtt);
}
```

---

## API Reference

### `mqtt_lib_init`
Connects to WiFi (blocking) then starts the MQTT client.

### `mqtt_lib_publish(handle, topic, payload, len, qos, retain)`
Publishes a message. Pass `len = -1` to use `strlen(payload)`.

### `mqtt_lib_subscribe(handle, topic, qos)`
Subscribes to a topic filter (supports `+` and `#` wildcards).

### `mqtt_lib_unsubscribe(handle, topic)`
Unsubscribes from a topic.

### `mqtt_lib_is_connected(handle)`
Returns `true` when the MQTT session is active.

### `mqtt_lib_deinit(handle)`
Disconnects and frees all resources.

---

## TLS Example

```c
mqtt_tls_config_t tls = {
    .ca_cert     = my_ca_pem,       // PEM string
    .client_cert = my_cert_pem,     // for mTLS (optional)
    .client_key  = my_key_pem,      // for mTLS (optional)
    .skip_cert_verify = false,
};

mqtt_broker_config_t broker = {
    .broker_uri = "mqtts://my.broker.io:8883",
    .tls        = &tls,
};
```

---

## Last Will and Testament

```c
mqtt_broker_config_t broker = {
    .broker_uri  = "mqtt://broker.example.com:1883",
    .lwt_topic   = "devices/esp32/status",
    .lwt_message = "offline",
    .lwt_qos     = 1,
    .lwt_retain  = 1,
};
```

---

## Requirements

- ESP-IDF **≥ 4.4** (tested on 5.x)
- PlatformIO with `platform = espressif32`
- `esp_mqtt` component (bundled with IDF)

---

## License

MIT
