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

constexpr unsigned long TIME_LIMIT(19UL * 60UL * 1000UL); // 19 mins + 1 min in delay for shutdown

// WiFi credentials
const char *WIFI_SSID = "aurobotics-ap";
const char *WIFI_PASSWORD = "12345678";

// MQTT broker settings
const char *MQTT_BROKER = "192.168.1.101";
const int MQTT_PORT = 1883;
const char *MQTT_USER = nullptr;     // Optional
const char *MQTT_PASSWORD = nullptr; // Optionalf

// network settings
bool AS_ACCESS_POINT = false;

// mqtt topics
constexpr char *STATUS_TOPIC = "float/status";
constexpr char *DATA_TOPIC = "float/data";
constexpr char *DEPTH_TOPIC = "float/depth";
constexpr char *END_TOPIC = "float/end";
constexpr char *SEND_NOW_TOPIC = "float/send_now";
constexpr char *CREDENTIAL_TOPIC = "float/data/credential";
constexpr char *ERROR_TOPIC = "float/error";

bool on_surface = true;

void yala_beina_nUpload();
bool connectToNetwork(bool asAccessPoint = false);
void setMessageOnCallBack();
void shutdown();
void mqttSetup();
void always_handle_network_ota_mqtt();
void myDelay(unsigned long ms);

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
Led currentState = CONNECTION;
constexpr int POWER = 23; // pin set high to retain power, set low to shut down

#define MAX_WIFI_RETRY_COUNT 5

#ifdef DRY_TEST
float test_depths[] = {2, 0.4, 2, 0.4, 0};
int current_target_index = 0;
#endif

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
    // pinMode(RUNNING, OUTPUT);
    // pinMode(UPLOADING, OUTPUT);
    // pinMode(CONNECTION, OUTPUT);
    pinMode(POWER, OUTPUT);
    // pinMode(BLINKING_LED, OUTPUT);
}

unsigned long powerTimeout;

void setup()
{
    delay(100);
    powerTimeout = millis();
    initPins();
    digitalWrite(POWER, HIGH); // set high to retain power

    Serial.begin(115200);

    if (!connectToNetwork())
    {
        // digitalWrite(CONNECTION, LOW); // turn off connection LED
        Serial.println("Failed to connect to network");

        // extreme error - all LEDs on
        // digitalWrite(UPLOADING, HIGH);
        // digitalWrite(RUNNING, HIGH);
        // digitalWrite(CONNECTION, HIGH);

        delay(1000);
        ESP.restart();
    }
    // digitalWrite(UPLOADING, LOW);
    // digitalWrite(RUNNING, LOW);
    // digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on

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
        // digitalWrite(CONNECTION, HIGH);
        myDelay(1000);
        // digitalWrite(CONNECTION, LOW);

        if (connectToWiFi(WIFI_SSID, WIFI_PASSWORD)) // try to connect to WiFi once than pass through otupdate if false
        {
            break;
        }
    }
    // digitalWrite(RUNNING, HIGH); // turn on running LED to indicate device is running and connected to network

    mqttSetup();

#ifndef DRY_TEST
    // Wire.begin();
    Wire.begin();
    // setup and calibrate pressure sensor only if NOT testing
    if (!pressureSensor.begin())
    {
        Serial.println("Failed to initialize MS5611 sensor!, if failed after 60 seconds, restarting...");
        // Absoute ERROR - all LEDs on
        // digitalWrite(UPLOADING, HIGH);
        MqttManager.publish(ERROR_TOPIC, "Failed to initialize MS5611 sensor");
        myDelay(60000);              // wait for 60 seconds to allow for OTA update if that was the issue, then try again and restart if it still fails
        if (!pressureSensor.begin()) // try again before restarting
        {
            MqttManager.publish(ERROR_TOPIC, "Failed to initialize MS5611 sensor on second attempt, restarting...");
            ESP.restart();
        }
        else
        {
            MqttManager.publish(STATUS_TOPIC, "MS5611 sensor initialized successfully on second attempt");
            Serial.println("MS5611 sensor initialized successfully on second attempt");
        }
    }

#endif

    // Start the sequence
    if (!store_data_setup())
    {
        Serial.println("Failed to setup data storage!, if failed after 60 seconds, restarting...");
        // Absoute ERROR - all LEDs on
        // digitalWrite(UPLOADING, HIGH);
        MqttManager.publish(ERROR_TOPIC, "Failed to setup data storage");
        myDelay(60000);
        if (!store_data_setup()) // try again before restarting
        {
            MqttManager.publish(ERROR_TOPIC, "Failed to setup data storage on second attempt, restarting...");
            Serial.println("Failed to setup data storage on second attempt, restarting...");
            ESP.restart();
        }
        else
        {
            MqttManager.publish(STATUS_TOPIC, "Data storage setup successful on second attempt");
            Serial.println("Data storage setup successful on second attempt");
        }
    }
    // digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on
    // digitalWrite(UPLOADING, LOW);   // turn on uploading LED to indicate device is collecting data and doing operations

    while (currentState != RUNNING)
    {
        if ((millis() - powerTimeout) >= TIME_LIMIT)
        {
            MqttManager.publish(ERROR_TOPIC, "Power timeout reached, shutting down in 60 seconds...");
            myDelay(60000);
            shutdown();
        }
        myDelay(100); // wait for command to start data collection
    }

    Serial.println("sending: \"Device started and about to collect data\"");
    MqttManager.publish(STATUS_TOPIC, "Device started and about to collect data");
    Serial.println("sent initial status message to MQTT broker");

#ifndef DRY_TEST
    // setting up buoyancy logic
    if (!buoyancy_setup(false))
    {
        Serial.println("Failed to setup buoyancy logic!, if failed after 60 seconds, restarting...");
        // Absoute ERROR - all LEDs on
        // digitalWrite(UPLOADING, HIGH);
        MqttManager.publish(ERROR_TOPIC, "Failed to setup buoyancy logic");
        myDelay(60000);             // wait for 60 seconds to allow for OTA update if that was the issue, then try again and restart if it still fails
        if (!buoyancy_setup(false)) // try again before restarting
        {
            MqttManager.publish(ERROR_TOPIC, "Failed to setup buoyancy logic on second attempt, restarting...");
            Serial.println("Failed to setup buoyancy logic on second attempt, restarting...");
            ESP.restart();
        }
        else
        {
            Serial.println("Buoyancy logic setup successfully on second attempt");
            MqttManager.publish(STATUS_TOPIC, "Buoyancy logic setup successfully on second attempt");
        }
    }
#endif
}

void loop()
{
    if ((millis() - powerTimeout) >= TIME_LIMIT)
    {
        if(on_surface)
            MqttManager.publish(ERROR_TOPIC, "Power timeout reached, shutting down in 60 seconds...");
        myDelay(60000);
        shutdown();
    }

    if (currentState == RUNNING)
    {
        Serial.println("Collecting data...");

#ifndef DRY_TEST // get depth from pressure sensor only if NOT dry testing
        // depth = pressureSensor.getDepth();
        depth = getDepth();
        if(depth  < 0.02)
            on_surface = true;
        else
            on_surface = false;
        if(on_surface)
            always_handle_network_ota_mqtt(); // Handle OTA updates in every loop iteration

        // buoyancy loop        
        buoyancy_loop(depth);

        // To store depth per time
        store_data_loop(depth);
#endif
#ifdef DRY_TEST // For testing depth changes without sensor
        if (abs(depth - test_depths[current_target_index]) < 0.05)
        {
            Serial.println("At target depth, holding...");
            myDelay(1000); // hold at target depth for 5 seconds
            current_target_index++;
            if (current_target_index >= 4)
            {
                currentState = UPLOADING;
                Serial.println("Test complete. Transitioning to UPLOADING state...");
            }
        }
        else if (depth > test_depths[current_target_index])
        {
            depth -= 0.1; // Move slightly below target
        }
        else
        {
            depth += 0.1;
        }
#endif

#ifdef PRESSURE_SENSOR_TEST
        MqttManager.publish(DEPTH_TOPIC, String(depth).c_str());
        Serial.print("Current Depth: ");
        Serial.println(depth);
#endif

        Serial.print("Current Target: ");
        Serial.println(getCurrentTarget());
        Serial.print("Current Depth: ");
        Serial.println(depth);
        if(on_surface)
            MqttManager.publish(DEPTH_TOPIC, String(depth).c_str());

#ifdef DRY_TEST
        // digitalWrite(BLINKING_LED, HIGH);
        myDelay(500); // for testing, in real scenario this would be based on sensor reading frequency
        // digitalWrite(BLINKING_LED, LOW);
#endif

        if (isComplete())
        {
            Serial.println("Data collection complete. Transitioning to UPLOADING state...");
            if(on_surface)
                MqttManager.publish(STATUS_TOPIC, "2bset, run ended, complete file ready for receive");
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

void shutdown()
{
    save_rotations();

    MqttManager.publish(STATUS_TOPIC, "Device shutting down");

    // turn off all LEDs to indicate shutdown
    // digitalWrite(CONNECTION, LOW);
    // digitalWrite(RUNNING, LOW);
    // digitalWrite(UPLOADING, LOW);
    digitalWrite(POWER, LOW); // turn off power to shut down device

    ESP.restart(); // restart m4 3aref leih
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

        if (!strcmp(topic.c_str(), END_TOPIC))
        {
            if (!strcmp(payload.c_str(), "shutdown"))
            {
                Serial.println("Received shutdown command. Ending run...");
                shutdown();
                
            }
            else
            {
                Serial.println("Received unknown command on float/end topic");
            }
        }

        if (!strcmp(topic.c_str(), SEND_NOW_TOPIC))
        {
            if(!payload.empty()){
            Serial.println("I need to send data now, 27eih yala wa nekamel b3dein");
            yala_beina_nUpload();
            }
        } 
        
        if (!strcmp(topic.c_str(), STATUS_TOPIC))
        {
            if(!strcmp(payload.c_str(), "start"))
            {
                Serial.println("Received command to start data collection");
                currentState = RUNNING;
            }
        } });
}

void yala_beina_nUpload()
{
    // digitalWrite(UPLOADING, HIGH); // turn on uploading LED to indicate device is uploading data to MQTT broker
    // digitalWrite(RUNNING, LOW);
    // MQTT setup
    Serial.println("Connecting to MQTT broker...");

    // Ensure WiFi is still connected before checking MQTT state
    if (WiFi.status() != WL_CONNECTED)
    {
        // digitalWrite(CONNECTION, LOW); // turn off connection LED
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

        // digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on

        // if mode is AP and AS_ACCESS_POINT is false then there is a problem
        while (!AS_ACCESS_POINT && WiFi.getMode() == WIFI_AP)
        {
            Serial.println("set up as Access Point unintentionally");
            otaupdate(); // Handle OTA updates

            // flucctualting led if AP
            // digitalWrite(CONNECTION, HIGH);
            myDelay(1000);
            // digitalWrite(CONNECTION, LOW);

            if (connectToWiFi(WIFI_SSID, WIFI_PASSWORD)) // try to connect to WiFi once than pass through otupdate if false
            {
                break;
            }
        }
    }
    // digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on

    // Handle MQTT communication
    MqttManager.loop(); // checks for mqtt connection and reconnects if needed

    Serial.println("trying to send Company Number and file to mqtt");

    Serial.print("Mqtt connection is: ");
    Serial.println(MqttManager.isConnected() ? "Connected" : "Not Connected");

    MqttManager.publish(CREDENTIAL_TOPIC, COMPANY_NUMBER);
    MqttManager.publishFileChunkedOverTopics(DATA_TOPIC, "/littlefs/log.csv", "log.csv");
    // Serial.println(millis() - t);
    myDelay(5000); // Send data every 5 seconds
}

void mqttSetup()
{
    IDFMQTTManager::setupState mqtt_state = MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
    while (!MqttManager.isConnected())
    {
        Serial.println("Error in connection to mqtt delaying in a while loop");
        delay(1000); // wait before retrying
        myDelay(1000);
    }

    MqttManager.loop(); // checks for mqtt connection and reconnects if needed

    // subscribe to topic that ends run and that sends instant file
    MqttManager.subscribe(END_TOPIC, 1);
    MqttManager.subscribe(SEND_NOW_TOPIC, 1);
    MqttManager.subscribe(STATUS_TOPIC, 1);
    setMessageOnCallBack();
}

void always_handle_network_ota_mqtt()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        // digitalWrite(CONNECTION, LOW); // turn off connection LED
        Serial.println("WiFi connection lost. Reconnecting...");
        WiFi.reconnect();
    }
    else
    {
        // Handle OTA updates
        otaupdate();
        // digitalWrite(CONNECTION, HIGH); // turn on connection LED if it was on
    }

    MqttManager.loop();             // if internet then reconnect to mqtt if not connected - non blocking
    yield();
}

void myDelay(unsigned long ms)
{
    unsigned long start = millis();
    while (millis() - start < ms)
    {
        always_handle_network_ota_mqtt();
        yield(); // Short delay to prevent watchdog timer reset
    }
}

// #include <Arduino.h>
// void setup(){
//     pinMode(23, OUTPUT);
//     digitalWrite(23, HIGH);
// }

// void loop(){
//     delay(1000);
// }