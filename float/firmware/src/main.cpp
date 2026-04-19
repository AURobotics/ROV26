#include "miscellaneous.h"

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

    MqttManager.setup(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD);
    MqttManager.loop(); // checks for mqtt connection and reconnects if needed

    // subscribe to topic that ends run
    MqttManager.subscribe("float/end", 1);
    setMessageOnCallBack();

    Serial.println("sending: \"Device started and about to collect data\"");
    MqttManager.publish("float/status", "Device started and about to collect data");
    Serial.println("sent initial status message to MQTT broker");
}

void loop()
{
    // unsigned long t = millis();
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

        // To store depth per time
        store_data_loop();

#ifndef DRY_TEST // get depth from pressure sensor only if NOT dry testing
        depth = pressureSensor.getDepth();
        setDepth(depth);
#endif

#ifdef PRESSURE_SENSOR_TEST
        MqttManager.publish("float/depth", String(depth).c_str());
        Serial.print("Current Depth: ");
        Serial.println(depth);
#endif

#ifdef DRY_TEST // For testing depth changes without sensor
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
            depth -= 0.1; // Move slightly below target
        }
        else
        {
            depth += 0.1;
        }
        setDepth(depth);
#endif

        Serial.print("Current Target: ");
        Serial.println(getCurrentTarget());
        Serial.print("Current Depth: ");
        Serial.println(depth);

#ifdef DRY_TEST
        digitalWrite(BLINKING_LED, HIGH);
        myDelay(500); // for testing, in real scenario this would be based on sensor reading frequency
        digitalWrite(BLINKING_LED, LOW);
#endif

        if (isComplete())
        {
            Serial.println("Data collection complete. Transitioning to UPLOADING state...");
            currentState = UPLOADING;
        }
    }
    else if (currentState == UPLOADING) // keep sending data to MQTT broker every 5 seconds till shutdown
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
}