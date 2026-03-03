#pragma once
#include "pwm.h"


class Motor {
    enum class HandlerType : uint8_t { FUNCTION, PWM } handler_type;

    union {
        struct Pwm_handler {
            PWM* p1;
            PWM* p2;
        } pwm_handler;
        void (*handler_function)(float);
    } Handler{};

    explicit Motor(void (*fn)(float)) : handler_type(HandlerType::FUNCTION) {
        Handler.handler_function = fn;
    }

    explicit Motor(PWM* p1, PWM* p2) : handler_type(HandlerType::PWM) {
        Handler.pwm_handler.p1 = p1;
        Handler.pwm_handler.p2 = p2;
    }

    void setup() const;
    void move(float speed) const;
    void stop() const;
    static void move_motor(Motor motors[8], float speeds[8]);
};

// class Motor {
//     PWM& pwm1;
//     PWM& pwm2;
//     std::function<void(float)> handler{};
//
// public:
//     Motor( PWM& p1,  PWM& p2);
//     explicit Motor(std::function<void(float)> Handler);
//     void setup() const;
//     void move(float speed) const;
//     void stop() const;
//     static void move_motor(Motor motors[8], float speeds[8]);
// };
