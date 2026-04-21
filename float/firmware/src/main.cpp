#include <Arduino.h>
#include <IDFMQTTClient.h>
#include "ota_manager.h"
#include <WiFi.h>
#include "store_data.h"
#include "idf_mqtt_manager.h"
#include <ms5611.h>
#include <buoyancy_lib.h>

#include "lan.h"

#define BLINKING_LED 2 // to make sure esp is ok :|

#define COMPANY_NUMBER "AU Robotics"

// WiFi credentials
const char *WIFI_SSID = "Vodafone_VDSL_3BE7";
const char *WIFI_PASSWORD = "Ee0123608241@";

// MQTT broker settings
const char *MQTT_BROKER = "192.168.1.9";
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optionalf

// network settings
bool AS_ACCESS_POINT = false;

void yala_beina_nUpload();
bool connectToNetwork(bool asAccessPoint = false);
void setMessageOnCallBack();

// ArduinoMqttManager MqttManager;
IDFMQTTManager MqttManager;

// pressure sensor
MS5611 pressureSensor = MS5611();
float depth = 0.0f;

enum Led
{
    RUNNING = 19,   // red
    UPLOADING = 5,  // blue // Collecting data and doing operations
    CONNECTION = 18 // green // Uploading data to MQTT broker
};
Led currentState;
constexpr int POWER = 23; // pin set high to retain power, set low to shut down

#define MAX_WIFI_RETRY_COUNT 5

// // timer to trigger if otaupdate stopped from being called
// hw_timer_t *otaWatchdogTimer = NULL;
// const int timeout_ms = 3000; // 1 seconds

// void callOtaupdate()
// {
//     // To reset: Restart the timer from 0
//     timerRestart(otaWatchdogTimer);

//     // Ensure the alarm is still active
//     timerWrite(otaWatchdogTimer, 0);

//     otaupdate();
// }

// // This function runs if the timer expires
// void IRAM_ATTR onTimer()
// {
//     digitalWrite(POWER, HIGH);
//     ESP.restart();
// }

void initPins()
{
    pinMode(RUNNING, OUTPUT);
    pinMode(UPLOADING, OUTPUT);
    pinMode(CONNECTION, OUTPUT);
    pinMode(POWER, OUTPUT);
    pinMode(BLINKING_LED, OUTPUT);
}

void setup()
{
    initPins();
    digitalWrite(POWER, HIGH); // set high to retain power

    Serial.begin(115200);

    if (!connectToNetwork())
    {
        digitalWrite(CONNECTION, LOW); // turn off connection LED
        Serial.println("Failed to connect to network");

        // extreme error - all LEDs on
        digitalWrite(UPLOADING, HIGH);
        digitalWrite(RUNNING, HIGH);
        digitalWrite(CONNECTION, HIGH);

        delay(1000);
        ESP.restart();
    }
    digitalWrite(UPLOADING, LOW);
    digitalWrite(RUNNING, LOW);
    digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on

    // OTA
    setupOTA();
    otaupdate();

    // Set up the watchdog timer to trigger if otaupdate is not called within the timeout period
    // otaWatchdogTimer = timerBegin(1000000); // 1 MHz, tick = 1 microsecond
    // timerAttachInterrupt(otaWatchdogTimer, &onTimer);
    // timerAlarm(otaWatchdogTimer, timeout_ms * 1000, true, 0); // tick = 1 microsecond; true for periodic

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

#ifndef DRY_TEST
    Wire.begin();
    // setup and calibrate pressure sensor only if NOT testing
    if (!pressureSensor.begin())
    {
        Serial.println("Failed to initialize MS5611 sensor!, if failed after 60 seconds, restarting...");
        // Absoute ERROR - all LEDs on
        digitalWrite(UPLOADING, HIGH);
        myDelay(60000);              // wait for 60 seconds to allow for OTA update if that was the issue, then try again and restart if it still fails
        if (!pressureSensor.begin()) // try again before restarting
        {
            ESP.restart();
        }
        else
        {
            Serial.println("MS5611 sensor initialized successfully on second attempt");
        }
    }

    // setting up buoyancy logic
    if (!buoyancy_setup(false))
    {
        Serial.println("Failed to setup buoyancy logic!, if failed after 60 seconds, restarting...");
        // Absoute ERROR - all LEDs on
        digitalWrite(UPLOADING, HIGH);
        myDelay(60000);             // wait for 60 seconds to allow for OTA update if that was the issue, then try again and restart if it still fails
        if (!buoyancy_setup(false)) // try again before restarting
        {
            ESP.restart();
        }
        else
        {
            Serial.println("Buoyancy logic setup successfully on second attempt");
        }
    }

#endif

    // Start the sequence
    if (!store_data_setup())
    {
        Serial.println("Failed to setup data storage!, if failed after 60 seconds, restarting...");
        // Absoute ERROR - all LEDs on
        digitalWrite(UPLOADING, HIGH);
        myDelay(60000);
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

    IDFMQTTManager::setupState mqtt_state = MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
    while (!MqttManager.isConnected())
    {
        Serial.println("Error in connection to mqtt delaying in a while loop");
        myDelay(1000);
    }

    MqttManager.loop(); // checks for mqtt connection and reconnects if needed

    // subscribe to topic that ends run and that sends instant file
    MqttManager.subscribe("float/end", 1);
    MqttManager.subscribe("float/send_now", 1);
    setMessageOnCallBack();

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
        MqttManager.loop();             // if internet then reconnect to mqtt if not connected - non blocking
    }

    // Handle OTA updates
    otaupdate();

    if (currentState == RUNNING)
    {
        Serial.println("Collecting data...");

#ifndef DRY_TEST // get depth from pressure sensor only if NOT dry testing
        depth = pressureSensor.getDepth();

        // buoyancy loop
        buoyancy_loop(depth);
#endif

        // To store depth per time
        store_data_loop(depth);

#ifdef DRY_TEST // For testing depth changes without sensor
        if (abs(depth - getCurrentTarget()) < 0.05)
        {
            Serial.println("At target depth, holding...");
        }
        else if (depth > getCurrentTarget())
        {
            depth -= 0.1; // Move slightly below target
        }
        else
        {
            depth += 0.1;
        }
#endif

#ifdef PRESSURE_SENSOR_TEST
        MqttManager.publish("float/depth", String(depth).c_str());
        Serial.print("Current Depth: ");
        Serial.println(depth);
#endif

        Serial.print("Current Target: ");
        Serial.println(getCurrentTarget());
        Serial.print("Current Depth: ");
        Serial.println(depth);
        MqttManager.publish("float/depth", String(depth).c_str());

#ifdef DRY_TEST
        digitalWrite(BLINKING_LED, HIGH);
        myDelay(500); // for testing, in real scenario this would be based on sensor reading frequency
        digitalWrite(BLINKING_LED, LOW);
#endif

        if (isComplete())
        {
            Serial.println("Data collection complete. Transitioning to UPLOADING state...");
            MqttManager.publish("float/data", "run ended, complete file ready for receive");
            currentState = UPLOADING;
        }
    }
    else if (currentState == UPLOADING) // keep sending data to MQTT broker every 5 seconds till shutdown
    {
        yala_beina_nUpload();
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
                save_rotations();
                
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
        }

        if (!strcmp(topic.c_str(), "float/send_now"))
        {
            if(!payload.empty()){
            Serial.println("I need to send data now, 27eih yala wa nekamel b3dein");
            yala_beina_nUpload();
            }
        } });
}

void yala_beina_nUpload()
{
    digitalWrite(UPLOADING, HIGH); // turn on uploading LED to indicate device is uploading data to MQTT broker
    digitalWrite(RUNNING, LOW);
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
    // Serial.println(millis() - t);
    myDelay(5000); // Send data every 5 seconds
}
