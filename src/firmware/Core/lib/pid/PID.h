#pragma once

class PID {
    double output_max;
    double output_min;
    double integral_max;
    double integral_min;
    double kp;
    double kd;
    double ki;
    double prev_measurement;
    // for low pass filter
    double filtered_derivative;
    double tau;
    double integral;

public:
    explicit constexpr PID(double kp, double kd, double ki);
    PID(const PID&) = delete; // copy constructor
    PID& operator=(const PID&) = delete;

    PID(PID&&) = default; // move constructor
    PID& operator=(PID&&) = default;

    void set_gains(double kp, double kd, double ki);
    void set_integral_limits(double integral_max, double integral_min);
    void set_output_limits(double output_max, double output_min);
    void set_derivative_filter(double tau);

    void reset();
    double update(double setpoint, double measurement, double dt);
};
