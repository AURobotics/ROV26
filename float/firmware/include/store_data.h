#ifndef STORE_DATA_H
#define STORE_DATA_H

void setDepth(float depth); // Reading from sensor
void startSequence();
bool isComplete();
float getCurrentTarget();
void clearLog();
void store_data_loop();
void store_data_setup();

#endif