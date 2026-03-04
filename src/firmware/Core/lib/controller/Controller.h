#pragma once
#include <optional>
#include "PID.h"

struct Controller {
    explicit constexpr Controller(PID angle_pid, std::optional<PID> rate_pid = std::nullopt) :
        angle_pid(std::move(angle_pid)), rate_pid(std::move(rate_pid)) {}

private:
    PID angle_pid;
    std::optional<PID> rate_pid;

public:
    float output(float setpoint, float angle, float dt, std::optional<float> rate = std::nullopt);

    void set_angle_pid(float kp, float ki, float kd) { angle_pid.set_gains(kp, ki, kd); }

    void set_rate_pid(float kp, float ki, float kd) {
        if (rate_pid.has_value()) {
            rate_pid->set_gains(kp, ki, kd);
        }
    }
};
