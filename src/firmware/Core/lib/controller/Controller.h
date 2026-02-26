#pragma once
#include "PID.h"
#include <optional>

struct Controller {
    explicit constexpr Controller(PID angle_pid, std::optional<PID> rate_pid = std::nullopt);

private:
    PID angle_pid;
    std::optional<PID> rate_pid;

public:
    float output(float setpoint, float angle, float dt, std::optional<float> rate = std::nullopt);
};