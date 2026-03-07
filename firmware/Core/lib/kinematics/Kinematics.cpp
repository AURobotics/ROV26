#include "Kinematics.h"
#include <cmath>

static constexpr float A_inv[8][6] = { { 0.25, -0.25,  0.0,   0.0,   0.0,  -0.25},
    { 0.25,  0.25,  0.0,   0.0,   0.0,   0.25},
    {-0.25,  0.25,  0.0,   0.0,   0.0,  -0.25},
    {-0.25, -0.25,  0.0,   0.0,   0.0,   0.25},

    { 0.0,   0.0,  -0.25, -0.25,  0.25,  0.0},
    { 0.0,   0.0,  -0.25,  0.25,  0.25,  0.0},
    { 0.0,   0.0,  -0.25, -0.25, -0.25,  0.0},
    { 0.0,   0.0,  -0.25,  0.25, -0.25,  0.0}
};


// buffer must be of size 8
void apply_pseudo_inverse(const float v[6], float* buffer) {
    for (int i = 0; i < 8; i++) {
        buffer[i] = 0.0f;
        for (int j = 0; j < 6; j++)
            buffer[i] += A_inv[i][j] * v[j];
    }
}

void normalize_thrusters(float output[8]) { // TODO: to be reduced
    float maxH = 0;
    float maxV = 0;
    for (int i = 0; i < 4; i++) {
        float val = std::fabs(output[i]);
        if (val > maxH)
            maxH = val;
    }

    if (maxH > 1.0f)
        for (int i = 0; i < 4; i++)
            output[i] /= maxH;

    for (int i = 4; i < 8; i++) {
        float val = std::fabs(output[i]);
        if (val > maxV)
            maxV = val;
    }
    if (maxV > 1.0f)
        for (int i = 4; i < 8; i++)
            output[i] /= maxV;
}
