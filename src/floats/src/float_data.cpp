#include <LittleFS.h>

// Simple target sequence
float targets[] = {0.4, 2.5, 0.4, 2.5, 0.4,0};
int currentTarget = 0;
float currentDepth = 0;
bool isRunning = false;
unsigned long lastLogTime = 0;


void setup() {
  Serial.begin(115200);
  
  // Initialize filesystem
  if (!LittleFS.begin(true)) {
    Serial.println("FS failed!");
    return;
  }
  
  // Create file with headers
  File file = LittleFS.open("/log.csv", FILE_WRITE);
  if (file) {
    file.println("time_ms,depth_cm,target_cm");
    file.close();
    Serial.println("Log file created");
  }
}

void loop() {
  
  // Log every second
  if (millis() - lastLogTime >= 333) {
    lastLogTime = millis();
    
    // Log current reading
    File file = LittleFS.open("/log.csv", FILE_APPEND);
    if (file) {
      file.printf("%lu,%.1f\n", millis(), currentDepth);
      file.close();
    }
    
    // Check if we reached target
    
  }
  if (abs(currentDepth - targets[currentTarget]) <= 0.05) {
      static unsigned long timer =millis();
      if(millis()-timer)
      currentTarget++;
      if (currentTarget >= 6) {
        isRunning = false;
        Serial.println("Sequence complete!");
      }
    }
}

// Call this to update current depth (from sensor)
void setDepth(float depth) {
  currentDepth = depth;
}

// Call this to start the sequence
void startSequence() {
  currentTarget = 0;
  isRunning = true;
  lastLogTime = millis();
  Serial.println("Sequence started");
}

// Call this to check status
bool isComplete() {
  return !isRunning;
}

// Call this to get current target
float getCurrentTarget() {
  return targets[currentTarget];
}

// Call this to clear data
void clearLog() {
  LittleFS.remove("/log.csv");
  File file = LittleFS.open("/log.csv", FILE_WRITE);
  if (file) {
    file.println("time_ms,depth_cm,target_cm");
    file.close();
  }
}