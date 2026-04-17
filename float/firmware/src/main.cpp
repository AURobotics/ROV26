#include <Arduino.h>
#include <ArduinoMQTTClient.h>
#include <IDFMQTTClient.h>
#include "ota_manager.h"
#include <WiFi.h>
#include "store_data.h"
#include "arduino_mqtt_manager.h"
#include "idf_mqtt_manager.h"
#include <ms5611.h>

#define COMPANY_NUMBER "AU Robotics"

// WiFi credentials
const char *WIFI_SSID = "Abdelaziz";
const char *WIFI_PASSWORD = "ya mosahel";

// MQTT broker settings
const char *MQTT_BROKER = "10.14.70.135";
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optional

// network settings
bool AS_ACCESS_POINT = false;

bool connectToNetwork(bool asAccessPoint = false);
bool connectToWiFi(const char *ssid, const char *password, int maxRetries = 0);
bool initAccessPoint(const char *ssid, const char *password, int maxRetries = 0);
void myDelay(unsigned long);
void subToMqttTopicToEndRun();

// ArduinoMqttManager MqttManager;
IDFMQTTManager MqttManager;

// depths values for testing ######################################
float depthIncrement = 0.1;

// pressure sensor
MS5611 pressureSensor = MS5611();
float depth = 0.0f;

enum Led
{
    RUNNING = 19, // red
    UPLOADING = 5, // blue // Collecting data and doing operations
    CONNECTION = 18 // green // Uploading data to MQTT broker
};
Led currentState;
constexpr int GATE = 23; // pin set high to retain power, set low to shut down

#define MAX_WIFI_RETRY_COUNT 5

void initPins()
{
    pinMode(RUNNING, OUTPUT);
    pinMode(UPLOADING, OUTPUT);
    pinMode(CONNECTION, OUTPUT);
    pinMode(GATE, OUTPUT);
}

void setup()
{
    initPins();
    digitalWrite(GATE, HIGH); // set high to retain power
    subToMqttTopicToEndRun();

    Serial.begin(115200);

    if (!connectToNetwork())
    {
        digitalWrite(CONNECTION, LOW); // turn off connection LED
        Serial.println("Failed to connect to network");
        delay(1000);
        ESP.restart();
    }
    digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on

    // OTA
    setupOTA();





    // if mode is AP and AS_ACCESS_POINT is false then there is a problem
    while (!AS_ACCESS_POINT && WiFi.getMode() == WIFI_AP)
    {
        Serial.println("set up as Access Point unintentionally");
        otaupdate(); // Handle OTA updates

        // flucctualting led if AP
        digitalWrite(CONNECTION, HIGH);
        myDelay(1000);
        digitalWrite(CONNECTION, LOW);

        if (connectToWiFi(WIFI_SSID, WIFI_PASSWORD)) // try to connect to WiFi once than pass through otupdate if false
        {
            break;
        }
    }
    digitalWrite(RUNNING, HIGH); // turn on running LED to indicate device is running and connected to network

    // setup and calibrate pressure sensor
    // COMMENTING OUT SENSOR LOGIC FOR TESTING WITHOUT SENSOR ############################
    // if (!pressureSensor.begin())
    // {
    //     Serial.println("Failed to initialize MS5611 sensor!, if failed after 30 seconds, restarting...");
    //     // Absoute ERROR - all LEDs on
    //     digitalWrite(UPLOADING, HIGH);
    //     myDelay(30000);
    //     if(!pressureSensor.begin()) // try again before restarting
    //     {
    //         ESP.restart();
    //     }
    //     else
    //     {
    //         Serial.println("MS5611 sensor initialized successfully on second attempt");
    //     }
    // }

    // Start the sequence
    if (!store_data_setup())
    {
        Serial.println("Failed to setup data storage!, if failed after 30 seconds, restarting...");
        // Absoute ERROR - all LEDs on
        digitalWrite(UPLOADING, HIGH);
        myDelay(30000);
        if (!store_data_setup()) // try again before restarting
        {
            ESP.restart();
        }
        else
        {
            Serial.println("Data storage setup successful on second attempt");
        }
    }
    digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on
    digitalWrite(UPLOADING, LOW);   // turn on uploading LED to indicate device is collecting data and doing operations
    currentState = RUNNING;

    MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
    MqttManager.loop(); // checks for mqtt connection and reconnects if needed
    Serial.println("sending: \"Device started and about to collect data\"");
    MqttManager.publish("float/status", "Device started and about to collect data");
    Serial.println("sent initial status message to MQTT broker");
}

void loop()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        digitalWrite(CONNECTION, LOW); // turn off connection LED
        Serial.println("WiFi connection lost. Reconnecting...");
        WiFi.reconnect();
    }
    else
    {
        digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on
        MqttManager.loop(); // if internet then reconnect to mqtt if not connected - non blocking
    }

    // Handle OTA updates
    otaupdate();

    if (currentState == RUNNING)
    {
        Serial.println("Collecting data...");

        // To store depth per time
        store_data_loop();

        // COMMENTING OUT SENSOR LOGIC FOR TESTING WITHOUT SENSOR ############################
        // depth = pressureSensor.getDepth();
        // setDepth(depth);

        // For testing depth changes without sensor #################################
        if (abs(depth - getCurrentTarget()) < 0.05)
        {
            Serial.println("At target depth, holding...");
            setDepth(depth);
            myDelay(1000); // Wait for 1 second
            setDepth(depth);
            myDelay(1000);
            setDepth(depth);
        }
        else if (depth > getCurrentTarget())
        {
            depth -= depthIncrement; // Move slightly below target
        }
        else
        {
            depth += depthIncrement;
        }
        setDepth(depth);

        Serial.print("Current Target: ");
        Serial.println(getCurrentTarget());
        Serial.print("Current Depth: ");
        Serial.println(depth);

        myDelay(500); // for testing, in real scenario this would be based on sensor reading frequency ############################################

        if (isComplete())
        {
            Serial.println("Data collection complete. Transitioning to UPLOADING state...");
            currentState = UPLOADING;
        }
    }
    else if (currentState == UPLOADING) // keep sending data to MQTT broker every 5 seconds till shutdown
    {
        // MQTT setup
        Serial.println("Connecting to MQTT broker...");

        // Ensure WiFi is still connected before checking MQTT state
        if (WiFi.status() != WL_CONNECTED)
        {
            digitalWrite(CONNECTION, LOW); // turn off connection LED
            if (!WiFi.reconnect())
            {
                WiFi.disconnect();
                if (!connectToNetwork())
                {
                    Serial.println("Failed to connect to network");
                    delay(1000);
                    ESP.restart(); // mothing we can do if we can't connect to network, restart and try again
                }
            }

            digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on

            // if mode is AP and AS_ACCESS_POINT is false then there is a problem
            while (!AS_ACCESS_POINT && WiFi.getMode() == WIFI_AP)
            {
                Serial.println("set up as Access Point unintentionally");
                otaupdate(); // Handle OTA updates

                // flucctualting led if AP
                digitalWrite(CONNECTION, HIGH);
                myDelay(1000);
                digitalWrite(CONNECTION, LOW);

                if (connectToWiFi(WIFI_SSID, WIFI_PASSWORD)) // try to connect to WiFi once than pass through otupdate if false
                {
                    break;
                }
            }
        }
        digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on

        // Handle MQTT communication
        MqttManager.loop(); // checks for mqtt connection and reconnects if needed

        Serial.println("trying to send Company Number and file to mqtt");

        Serial.print("Mqtt connection is: ");
        Serial.println(MqttManager.isConnected() ? "Connected" : "Not Connected");

        MqttManager.publish("float/data/credential", COMPANY_NUMBER);
        MqttManager.publishFileChunkedOverTopics("float/data", "/littlefs/log.csv", "log.csv");
        myDelay(5000); // Send data every 5 seconds
    }
}

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

void myDelay(unsigned long ms)
{
    unsigned long start = millis();
    while (millis() - start < ms)
    {
        // Handle OTA updates during delay
        otaupdate();
        delay(100); // Short delay to prevent watchdog timer reset
    }
}

bool initAccessPoint(const char *ssid, const char *password, int maxRetries)
{
    IPAddress local_IP(192, 168, 1, 22);
    IPAddress gateway(192, 168, 1, 5);
    IPAddress subnet(255, 255, 255, 0);

    Serial.print("Setting up Access Point configuration... ");
    if (!WiFi.softAPConfig(local_IP, gateway, subnet))
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

void subToMqttTopicToEndRun()
{
    MqttManager.setCallbackOnMessage([](const std::string &topic, const std::string &payload)
                                     {
        Serial.print("Received message on topic: ");
        Serial.print(topic.c_str());
        Serial.print(" with payload: [");
        Serial.print(payload.c_str());
        Serial.println("]");

        if (topic == "float/end")
        {
            if(payload == "shutdown")
            {
                Serial.println("Received shutdown command. Ending run...");
                ESP.restart(); // restart to end the run
            }
            else
            {
                Serial.println("Received unknown command on float/end topic");
            }
        } });
    MqttManager.subscribe("float/end", 1);
}
