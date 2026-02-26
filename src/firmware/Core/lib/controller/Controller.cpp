#include "Controller.h"


constexpr Controller::Controller(PID angle_pid, std::optional<PID> rate_pid) :
    angle_pid(std::move(angle_pid)), rate_pid(std::move(rate_pid)) {}

float Controller::output(const float setpoint, const float angle, const float dt,
                         const std::optional<float> rate) {
    if (rate.has_value()) {
        const auto angle_pid_output = static_cast<float>(angle_pid.update(setpoint, angle, dt));
        return static_cast<float>(rate_pid->update(angle_pid_output, *rate, dt));
    }
    return static_cast<float>(angle_pid.update(setpoint, angle, dt));
}
