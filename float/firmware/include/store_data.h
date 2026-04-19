#ifndef STORE_DATA_H
#define STORE_DATA_H

#include <Arduino.h>

extern const char *LOG_FILE;

void store_data_loop(float depth);
\ void clearLog();
bool store_data_setup();

#endif