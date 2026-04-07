#include "store_data.h"
#include <LittleFS.h>

const char *LOG_FILE = "/log.csv";

void startSequence();
// Target sequence
float targets[] = {2.5, 0.4, 2.5, 0.4, 0};
int currentTarget = 0;
float currentDepth = 0;
bool isRunning = false;
unsigned long lastLogTime = 0;
unsigned long holdTimer = 0;

bool store_data_setup()
{

  // Initialize filesystem
  if (!LittleFS.begin(true))
  {
    Serial.println("FS failed!");
    return false;
  }

  // Create file with headers
  File file = LittleFS.open(LOG_FILE, FILE_WRITE);
  if (file)
  {
    file.println("time_ms,depth_cm");
    file.close();
    Serial.println("Log file created");
  }
  return true;
  startSequence();
}

void store_data_loop()
{
  if (isRunning)
  {
    // Log 3 times every second
    if (millis() - lastLogTime >= 333)
    {
      lastLogTime = millis();

      // Log current reading
      File file = LittleFS.open(LOG_FILE, FILE_APPEND);
      if (file)
      {
        file.printf("%lu,%.1f\n", millis(), currentDepth);
        file.close();
      }
    }

    // Check if we reached the target
    if (currentTarget < 5 && abs(currentDepth - targets[currentTarget]) <= 0.05)
    {

      // If timer is 0, this is the first time reaching this target
      if (holdTimer == 0)
      {
        holdTimer = millis();
      }

      // If 30 seconds have passed
      if (millis() - holdTimer >= 30000)
      {
        currentTarget++;
        holdTimer = 0; // Reset timer for next target

        if (currentTarget >= 5)
        {
          isRunning = false;
          Serial.println("Sequence complete!");
        }
      }
    }
    else
    {
      // Not at target, reset timer
      holdTimer = 0;
    }
  }
}

// Call this to update current depth (from sensor)
void setDepth(float depth)
{
  currentDepth = depth;
}

// Call this to start the sequence
void startSequence()
{
  currentTarget = 0;
  holdTimer = 0;
  isRunning = true;
  lastLogTime = millis();
  Serial.println("Sequence started");
}

// Call this to check status
bool isComplete()
{
  return !isRunning;
}

// Call this to get current target
float getCurrentTarget()
{
  return targets[currentTarget];
}

// Call this to clear data
void clearLog()
{
  LittleFS.remove(LOG_FILE);
  File file = LittleFS.open(LOG_FILE, FILE_WRITE);
  if (file)
  {
    file.println("time_ms,depth_cm");
    file.close();
  }
}