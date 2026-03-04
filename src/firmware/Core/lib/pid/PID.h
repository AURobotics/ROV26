#pragma once

class PID {
    double output_max = 1;
    double output_min = -1;
    double integral_max = 100;
    double integral_min = -100;
    double kp;
    double kd;
    double ki;
    double prev_measurement = 0;
    // for low pass filter
    double filtered_derivative = 0;
    double tau = 0.1; // needs to be tuned
    double integral = 0;

public:
    explicit constexpr PID(double kp, double kd, double ki): kp(kp), kd(kd), ki(ki) {}
    PID(const PID&) = delete; // copy constructor
    PID& operator=(const PID&) = delete;

    PID(PID&&) = default; // move constructor
    PID& operator=(PID&&) = default;

    void set_gains(double _kp, double _kd, double _ki);
    void set_integral_limits(double _integral_max, double _integral_min);
    void set_output_limits(double _output_max, double _output_min);
    void set_derivative_filter(double _tau);

    void reset();
    double update(double setpoint, double measurement, double dt);
};
