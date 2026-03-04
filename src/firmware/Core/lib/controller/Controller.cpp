#include "Controller.h"



float Controller::output(const float setpoint, const float angle, const float dt,
                         const std::optional<float> rate) {
    if (rate.has_value()) {
        const auto angle_pid_output = static_cast<float>(angle_pid.update(setpoint, angle, dt));
        return static_cast<float>(rate_pid->update(angle_pid_output, *rate, dt));
    }
    return static_cast<float>(angle_pid.update(setpoint, angle, dt));
}

void Controller::set_angle_pid(float kp, float ki, float kd) { angle_pid.set_gains(kp, ki, kd); }

void Controller::set_rate_pid(float kp, float ki, float kd) {
    if (rate_pid.has_value()) {
        rate_pid->set_gains(kp, ki, kd);
    }
}
