#ifndef LAN_H
#define LAN_H

#include <WiFi.h>
#include "ota_manager.h"

bool connectToWiFi(const char *ssid, const char *password, int maxRetries = 0);
bool initAccessPoint(const char *ssid, const char *password, int maxRetries = 0);

#endif