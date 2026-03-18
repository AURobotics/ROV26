#include <Arduino.h>
#include <TMCStepper.h>
#include <HardwareSerial.h>

#define R_SENSE 0.11f //to be changed
#define SERIAL Serial1
#define K_P 0.086
#define K_I 0.00879
#define K_D 0.187
#define MAX_MOTOR_VEL 10
#define MAX_DISTANCE 10

class PID{
    public:
        PID(float Kp, float Ki, float Kd, float max_motor_output){
            this->Kp = Kp;
            this->Ki = Ki;
            this->Kd = Kd;
            float max_clearance = 0.98; //better practice to assume the motor cant reach 100% output, this variable is used for windup checking
            this->max_motor_output = max_motor_output * max_clearance;
        }
        float Kp, Ki, Kd;
        float max_motor_output;
        float current_integral = 0;
        float prev_error = 0;
        float prev_time = 0;
        float prev_D = 0;
        float set_point;
        float calculate_error(float current_reading){
            return this->set_point - current_reading;
        }
        float calculate_PID(float error, float time_stamp){
            float P = this->Kp * error;
            this->current_integral += error * (time_stamp - this->prev_time);
            float I = this->Ki * this->current_integral;
            //anti windup starts here
            if(I > this->max_motor_output){ 
                this->current_integral = this->max_motor_output / Ki;
                I = this->current_integral * this->Ki;
            }
            else if(I < -this->max_motor_output){
                this->current_integral = -this->max_motor_output / Ki;
                I = this->current_integral * this->Ki;
            }
            //anti windup ends here
            float D;
            if(time_stamp - this->prev_time == 0) //make sure to not divide by 0
                D = prev_D;
            else
                D = Kd * (error - this->prev_error) / (time_stamp - this->prev_time);
            this->prev_error = error;
            this->prev_time = time_stamp;
            this->prev_D = D;
            float PID = P+I+D;
            if(PID > this->max_motor_output){
                PID = this->max_motor_output;
            }
            else if(PID < -this->max_motor_output){
                PID = -this->max_motor_output;
            }
            return PID;
        }
};

TMC2208Stepper driver = TMC2208Stepper(&SERIAL, R_SENSE);
PID pid = PID(K_P,K_I,K_D,MAX_MOTOR_VEL); //to be added: PID parameters + max motor output
float time;
bool hold_position = false;
void setup() {
  // put your setup code here, to run once:
  SERIAL.begin(115200);
  driver.begin();
  //what about sense resistors?
  driver.toff(5);
  driver.pwm_autoscale(true);
  driver.pdn_disable(true); //allow UART to control (not only configure)
  // driver.I_scale_analog(false); //use internal reference derived from 5VOUT
  driver.mstep_reg_select(true);

  pid.set_point = -2.5; //initial set point
  time = millis(); //start time
}


void loop() {
  // put your main code here, to run repeatedly:
  if(hold_position && millis() - time > 1000 * 30){ //if we have been holding position for 30 seconds, we flip direction
    pid.set_point = -2.5 - pid.set_point; //flip motor direction after being stable for 30 seconds
    pid.current_integral = 0; //reset integral to help change direction faster
    hold_position = false;
  }
  float height = get_height(); //get height from pressure sensor
  float error = pid.calculate_error(height);
  if(!hold_position && error < 0.3){ //error less than 30 cm
    hold_position = true; //start holding position
    time = millis();
  }
  float signal = pid.calculate_PID(error, millis());
  driver.VACTUAL(signal);
}
