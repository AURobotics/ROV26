#pragma once


void normalize_thrusters(float output[8]);

/**
 * @brief apply pseudo inverse -> normalize thrusters
 * @param v forces vector
 * @param buffer function's output, must be of size 8
 */
void apply_pseudo_inverse(const float v[6], float* buffer);

