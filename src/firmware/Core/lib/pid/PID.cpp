#include "PID.h"

constexpr PID::PID(double kp, double kd, double ki) : kp(kp), kd(kd), ki(ki) {}

void PID::set_gains(const double _kp, const double _kd, const double _ki) {
    this->kp = _kp;
    this->kd = _kd;
    this->ki = _ki;
}

void PID::set_integral_limits(const double _integral_max, const double _integral_min) {
    this->integral_max = _integral_max;
    this->integral_min = _integral_min;
}

void PID::set_output_limits(const double _output_max, const double _output_min) {
    this->output_max = _output_max;
    this->output_min = _output_min;
}

void PID::set_derivative_filter(const double _tau) { this->tau = _tau; }

void PID::reset() {
    prev_measurement = 0;
    integral = 0;
    filtered_derivative = 0;
}

double PID::update(const double setpoint, const double measurement, const double dt) {
    double error = setpoint - measurement;
    // to prevent overshoot on zero-crossings
    // // don't know if I should zero out
    // the integral if they are different signs or if this is ok
    if (error * integral >= 0)
        integral += error * dt;

    double raw_derivative = -(measurement - prev_measurement) /
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
