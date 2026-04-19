#include "miscellaneous.h"


bool connectToNetwork(bool asAccessPoint)
{
    if (asAccessPoint)
    {
        initAccessPoint(WIFI_SSID, WIFI_PASSWORD, MAX_WIFI_RETRY_COUNT);
    }
    else
    {
        if (!connectToWiFi(WIFI_SSID, WIFI_PASSWORD, MAX_WIFI_RETRY_COUNT))
        {
            Serial.println("Failed to connect to WiFi -> trying to set up as Access Point");
            AS_ACCESS_POINT = true;
            if (!initAccessPoint(WIFI_SSID, WIFI_PASSWORD, MAX_WIFI_RETRY_COUNT))
            {
                Serial.println("Failed to initialize Access Point");
                return false;
            }
        }
    }
    return true;
}

bool connectToWiFi(const char *ssid, const char *password, int maxRetries)
{
    Serial.print("Connecting to WiFi");

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    int retryCount = 0;

    while (retryCount < maxRetries)
    {
        int attempts = 0;
        int maxAttempts = 60; // 30 seconds

        while (WiFi.status() != WL_CONNECTED && attempts < maxAttempts)
        {
            myDelay(500);
            Serial.print(".");
            attempts++;
        }

        if (WiFi.status() == WL_CONNECTED)
        {
            Serial.println("\nWiFi connected");
            Serial.print("IP address: ");
            Serial.println(WiFi.localIP());
            return true;
        }

        Serial.println("status: " + String(WiFi.status()));
        retryCount++;
        Serial.printf("\nConnection failed. Retry %d of %d...\n", retryCount, maxRetries);
    }

    Serial.println("\nWiFi connection failed after all retries!");
    return false;
}

void myDelay(unsigned long ms, bool resetOtaWatchdog)
{
    unsigned long start = millis();
    while (millis() - start < ms)
    {
        // Handle OTA updates during delay
        if (resetOtaWatchdog)
            otaupdate();
        else
            otaupdate();
        delay(100); // Short delay to prevent watchdog timer reset
    }
}

bool initAccessPoint(const char *ssid, const char *password, int maxRetries)
{
    IPAddress local_IP(192, 168, 1, 22);
    IPAddress POWERway(192, 168, 1, 5);
    IPAddress subnet(255, 255, 255, 0);

    Serial.print("Setting up Access Point configuration... ");
    if (!WiFi.softAPConfig(local_IP, POWERway, subnet))
    {
        Serial.println("FAILED!");
        Serial.println("Using default configuration instead");
        // continue without custom config and use data printed by WiFi.softAPIP() later to know the actual IP address
    }
    else
    {
        Serial.println("OK");
    }

    for (int attempt = 1; attempt <= maxRetries; attempt++)
    {
        Serial.printf("Starting Access Point (attempt %d of %d)... ", attempt, maxRetries);

        if (WiFi.softAP(ssid, password))
        {
            Serial.println("READY!");
            Serial.print("Access Point IP address: ");
            Serial.println(WiFi.softAPIP());
            Serial.printf("SSID: %s\n", ssid);
            return true;
        }

        Serial.println("FAILED!");
        if (attempt < maxRetries)
        {
            myDelay(1000);
        }
    }

    Serial.println("ERROR: Could not start Access Point!");
    return false;
}

void setMessageOnCallBack()
{
    MqttManager.setCallbackOnMessage([](const std::string &topic, const std::string &payload)
                                     {
        Serial.print("Received message on topic: ");
        Serial.print(topic.c_str());
        Serial.print(" with payload: [");
        Serial.print(payload.c_str());
        Serial.println("]");

        if (!strcmp(topic.c_str(),"float/end"))
        {
            if (!strcmp(payload.c_str(), "shutdown"))
            {
                Serial.println("Received shutdown command. Ending run...");
                // turn off all LEDs to indicate shutdown
                digitalWrite(CONNECTION, LOW);
                digitalWrite(RUNNING, LOW);
                digitalWrite(UPLOADING, LOW);
                digitalWrite(POWER, LOW); // turn off power to shut down device

                ESP.restart(); // restart m4 3aref leih
            }
            else
            {
                Serial.println("Received unknown command on float/end topic");
            }
        } });
}
