#include "PID.h"

PID::PID(double kp, double kd, double ki, double integral_max,
         double integral_min)
    : integral_max(integral_max), integral_min(integral_min), kp(kp), kd(kd),
      ki(ki) {

  prev_measurement = 0;
  filtered_derivative = 0;
  tau = 0.1; // needs to be tuned//  greater tau->less noisy, slower  // smaller
             // tau-> noisier,faster response
  integral = 0;
  output_max = 100;
  output_min = -100;
}

void PID::set_gains(double kp, double kd, double ki) {
  this->kp = kp;
  this->kd = kd;
  this->ki = ki;
}

void PID::set_integral_limits(double integral_max, double integral_min) {
  this->integral_max = integral_max;
  this->integral_min = integral_min;
}

void PID::set_output_limits(double output_max, double output_min) {
  this->output_max = output_max;
  this->output_min = output_min;
}

void PID::set_derivative_filter(double tau) { this->tau = tau; }

void PID::reset() {
  prev_measurement = 0;
  integral = 0;
  filtered_derivative = 0;
}

double PID::update(double setpoint, double measurement, double dt) {
  double error = setpoint - measurement;
  // to prevent overshoot on zero-crossings
  // // don't know if i should zero out
  // the integral if they are different signs or if this is ok
  if (error * integral >= 0)
    integral += error * dt;

  double raw_derivative =
      -(measurement - prev_measurement) /
      dt; //-ve 3ashan ana bab2a 3ayza a brake kol ma yesara3 aktar 3ashan a
          // insure smooth motion 8aleban ya3ny :)
          // low-pass filter + derivative--> N/(S+N)(low pass) * S(derivative)
          // dt/(tau+dt)-->time domain approximation of frequency domain
          // representation 1/(tau*S+1)
  double filter_coef = dt / (tau + dt);
  filtered_derivative += filter_coef * (raw_derivative - filtered_derivative);

  // anti-windup
  if (integral > integral_max)
    integral = integral_max;
  else if (integral < integral_min)
    integral = integral_min;
  double output = (kp * error) + (ki * integral) + (kd * filtered_derivative);

  // min/max limits
  if (output > output_max)
    output = output_max;
  else if (output < output_min)
    output = output_min;

  prev_measurement = measurement;
  return output;
}
