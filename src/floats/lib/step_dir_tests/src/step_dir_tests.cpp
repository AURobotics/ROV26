#include <step_dir_tests.h>

void calibrate(){
  for(int i = 0; i < 160; i++){
    digitalWrite(STEP_PIN, HIGH);
    delay(10);
    digitalWrite(STEP_PIN, LOW);
    delay(10);
  }
}

void test_setup(){
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(EN_PIN, OUTPUT); 
  digitalWrite(EN_PIN, HIGH);
  digitalWrite(DIR_PIN, HIGH);
  // digitalWrite(STEP_PIN, HIGH);
  Serial.begin(9600);
  delay(5000);
  Serial.println("started");
  calibrate();

}


void accelerate(){
  int target_speed = 100;
  int current_delay = 20;
  int target_delay = 1;

  //accelerate2
  target_delay = 125;
  for (current_delay = 1200; current_delay > target_delay; current_delay -= 1){
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(current_delay);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(current_delay);
  }
  //constant
  for(int i = 0; i < STEPS_PER_REVOLUTION * 16 * 5; i++){
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(target_delay);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(target_delay);
  }
  //decelerate1
  target_delay = 1200;
  for (; current_delay < target_delay; current_delay += 1){
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(current_delay);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(current_delay);
  }
  //stop
}

void test_loop(){
  digitalWrite(EN_PIN, LOW);
  Serial.println("active");
  calibrate();
  accelerate();
  Serial.println("inactive");
  digitalWrite(EN_PIN, HIGH);
  delay(7000);
}