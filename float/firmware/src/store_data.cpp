#include "store_data.h"
#include <LittleFS.h>

const char *LOG_FILE = "/log.csv";

unsigned long lastLogTime = 0;

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
}

void store_data_loop(float depth)
{
  // Log every 5 secs
  if (millis() - lastLogTime >= 5000)
  {
    lastLogTime = millis();

    // Log current reading
    File file = LittleFS.open(LOG_FILE, FILE_APPEND);
    if (file)
    {
      file.printf("%lu,%.1f\n", millis(), depth);
      file.close();
    }
  }
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