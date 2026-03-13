#include "mpu9250.h"
#include <cstring>

#include "usbd_cdc_if.h"

int16_t accelCount[3];  // Stores the 16-bit signed accelerometer sensor output
int16_t gyroCount[3];   // Stores the 16-bit signed gyro sensor output
int16_t magCount[3];    // Stores the 16-bit signed magnetometer sensor output
float magCalibration[3] = {0, 0, 0}, magbias[3] = {0, 0, 0};  // Factory mag calibration and mag bias
float gyroBias[3] = {0, 0, 0}, accelBias[3] = {0, 0, 0}; // Bias corrections for gyro and accelerometer
float ax, ay, az, gx, gy, gz, mx, my, mz; // variables to hold latest sensor data values
int16_t tempCount;   // Stores the real internal chip temperature in degrees Celsius
float temperature;
float SelfTest[6];
CalibrationData calib;

int delt_t = 0; // used to control display output rate
int count = 0;  // used to control display output rate

// parameters for 6 DoF sensor fusion calculations
float PI = 3.14159265358979323846f;
float GyroMeasError = PI * (60.0f / 180.0f);     // gyroscope measurement error in rads/s (start at 60 deg/s), then reduce after ~10 s to 3
float beta = 0.1;//sqrt(3.0f / 4.0f) * GyroMeasError;  // compute beta
float GyroMeasDrift = PI * (1.0f / 180.0f);      // gyroscope measurement drift in rad/s/s (start at 0.0 deg/s/s)
float zeta = sqrt(3.0f / 4.0f) * GyroMeasDrift;  // compute zeta, the other free parameter in the Madgwick scheme usually set to a small or zero value

float pitch, yaw, roll;
float deltat = 0.0f;                             // integration interval for both filter schemes
int lastUpdate = 0, firstUpdate = 0, Now = 0;    // used to calculate integration interval                               // used to calculate integration interval
float q[4] = {1.0f, 0.0f, 0.0f, 0.0f};           // vector to hold quaternion
float eInt[3] = {0.0f, 0.0f, 0.0f};              // vector to hold integral error for Mahony method

constexpr uint32_t flash_address = 0x08020000;

MPU9250::MPU9250(I2C_HandleTypeDef *hi2c) : hi2c(hi2c) {}

HAL_StatusTypeDef MPU9250::writeByte(uint8_t devAddr, uint8_t regAddr, uint8_t data) {
    return HAL_I2C_Mem_Write(
        hi2c, devAddr, regAddr, I2C_MEMADD_SIZE_8BIT, &data, 1, HAL_MAX_DELAY);
}

uint8_t MPU9250::readByte(uint8_t devAddr, uint8_t regAddr) {
    uint8_t data = 0;
    HAL_I2C_Mem_Read(hi2c, devAddr, regAddr, I2C_MEMADD_SIZE_8BIT,&data,1,HAL_MAX_DELAY);
    return data;
}

HAL_StatusTypeDef MPU9250::readBytes(uint8_t devAddr, uint8_t regAddr, uint8_t count, uint8_t *dest) {
    return HAL_I2C_Mem_Read(hi2c,
                            devAddr,
                            regAddr,
                            I2C_MEMADD_SIZE_8BIT,
                            dest,
                            count,
                            HAL_MAX_DELAY);
}

void MPU9250::init() {
    resetMPU9250(); // Reset registers to default in preparation for device calibration
    calibrateMPU9250(gyroBias, accelBias); // Calibrate gyro and accelerometers, load biases in bias registers
    initMPU9250();
    initAK8963(magCalibration);

//     if(!loadCalibration(calib)) {
// }
}

void MPU9250::update() {
    static uint32_t lastTick = 0;
    uint32_t now = HAL_GetTick();
    deltat = (lastTick == 0) ? 0.01f : (now - lastTick) * 0.001f;
    lastTick = now;

    getAres();
    readAccelData(accelCount);  // Read the x/y/z adc values
    // Now we'll calculate the accleration value into actual g's
    ax = (float)accelCount[0]*aRes - accelBias[0];  // get actual g value, this depends on scale being set
    ay = (float)accelCount[1]*aRes - accelBias[1];
    az = (float)accelCount[2]*aRes - accelBias[2];
    // char buffer1[100];
    // int len = 0;
    // len +=sprintf(buffer1+len,"\n\rax = %f, ay = %f, az = %f",ax,ay,az);
    // CDC_Transmit_FS((uint8_t*)buffer1,len);

    getGres();
    readGyroData(gyroCount);  // Read the x/y/z adc values
    // Calculate the gyro value into actual degrees per second
    gx = (float)gyroCount[0]*gRes - gyroBias[0];  // get actual gyro value, this depends on scale being set
    gy = (float)gyroCount[1]*gRes - gyroBias[1];
    gz = (float)gyroCount[2]*gRes - gyroBias[2];
    // len =0;
    // len +=sprintf(buffer1+len,"\n\rgx = %f, gy = %f, gz = %f",gx,gy,gz);
    // CDC_Transmit_FS((uint8_t*)buffer1,len);

    getMres();
    readMagData(magCount);  // Read the x/y/z adc values
    // Calculate the magnetometer values in milliGauss
    // Include factory calibration per data sheet and user environmental corrections
    mx = (float)magCount[0]*mRes*magCalibration[0] - magbias[0];  // get actual magnetometer value, this depends on scale being set
    my = (float)magCount[1]*mRes*magCalibration[1] - magbias[1];
    mz = (float)magCount[2]*mRes*magCalibration[2] - magbias[2];
    // len =0;
    // len += sprintf(buffer1+len,"\n\rmx = %f , my = %f, mz = %f",mx,my,mz);
    // CDC_Transmit_FS((uint8_t*)buffer1,len);
    MadgwickQuaternionUpdate(ax, ay, az, gx*PI/180.0f, gy*PI/180.0f, gz*PI/180.0f,  mx,  my, mz);
}

void MPU9250::readAccelData(int16_t *destination) {
    uint8_t rawData[6];
    readBytes(MPU9250_ADDRESS, ACCEL_XOUT_H, 6, rawData);
    destination[0] = (int16_t)(((int16_t)rawData[0] << 8) | rawData[1]);
    destination[1] = (int16_t)(((int16_t)rawData[2] << 8) | rawData[3]);
    destination[2] = (int16_t)(((int16_t)rawData[4] << 8) | rawData[5]);

}

void MPU9250::readGyroData(int16_t *destination) {
    uint8_t rawData[6];
    readBytes(MPU9250_ADDRESS, GYRO_XOUT_H, 6, rawData);
    destination[0] = (int16_t)(((int16_t)rawData[0] << 8) | rawData[1]);
    destination[1] = (int16_t)(((int16_t)rawData[2] << 8) | rawData[3]);
    destination[2] = (int16_t)(((int16_t)rawData[4] << 8) | rawData[5]);
}

void MPU9250::readMagData(int16_t *destination) {
    uint8_t rawData[7];
    if (readByte(AK8963_ADDRESS, AK8963_ST1) & 0x01) {
        readBytes(AK8963_ADDRESS, AK8963_XOUT_L, 7, rawData);
        uint8_t c = rawData[6];
        if (!(c & 0x08)) {
            destination[0] = (int16_t)(((int16_t)rawData[1] << 8) | rawData[0]);
            destination[1] = (int16_t)(((int16_t)rawData[3] << 8) | rawData[2]);
            destination[2] = (int16_t)(((int16_t)rawData[5] << 8) | rawData[4]);
        }
    }
}

int16_t MPU9250::readTempData() {
    uint8_t rawData[2];
    readBytes(MPU9250_ADDRESS, TEMP_OUT_H, 2, rawData);
    return (int16_t)(((int16_t)rawData[0]) << 8 | rawData[1]);
}

// ─────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────

void MPU9250::resetMPU9250() {
    writeByte(MPU9250_ADDRESS, PWR_MGMT_1, 0x80);
    HAL_Delay(100);  // mbed: wait(0.1)
}

// ─────────────────────────────────────────────
// AK8963 Init
// ─────────────────────────────────────────────

void MPU9250::initAK8963(float *destination) {
    uint8_t rawData[3];
    writeByte(AK8963_ADDRESS, AK8963_CNTL, 0x00);
    HAL_Delay(10);   // mbed: wait(0.01)
    writeByte(AK8963_ADDRESS, AK8963_CNTL, 0x0F);
    HAL_Delay(10);
    readBytes(AK8963_ADDRESS, AK8963_ASAX, 3, rawData);
    destination[0] = (float)(rawData[0] - 128) / 256.0f + 1.0f;
    destination[1] = (float)(rawData[1] - 128) / 256.0f + 1.0f;
    destination[2] = (float)(rawData[2] - 128) / 256.0f + 1.0f;
    writeByte(AK8963_ADDRESS, AK8963_CNTL, 0x00);
    HAL_Delay(10);
    // Set 16-bit continuous measurement mode
    uint8_t mode = (uint8_t)(Mscale << 4 | 0x06);  // 0x06 = 100Hz
    writeByte(AK8963_ADDRESS, AK8963_CNTL, mode);
    HAL_Delay(10);
    char buffer1[100];
    int len = 0;
    len +=sprintf(buffer1+len,"\n\rmagCalibration = %f, %f, %f",destination[0],destination[1],destination[2]);
    CDC_Transmit_FS((uint8_t*)buffer1,len);
}

// ─────────────────────────────────────────────
// MPU9250 Init
// ─────────────────────────────────────────────

void MPU9250::initMPU9250() {
    writeByte(MPU9250_ADDRESS, PWR_MGMT_1, 0x00);
    HAL_Delay(100);  // mbed: wait(0.1)

    writeByte(MPU9250_ADDRESS, PWR_MGMT_1, 0x01);

    writeByte(MPU9250_ADDRESS, CONFIG, 0x03);
    writeByte(MPU9250_ADDRESS, SMPLRT_DIV, 0x04);  // 200 Hz

    // Gyro config — read modify write to preserve other bits
    uint8_t c = readByte(MPU9250_ADDRESS, GYRO_CONFIG);
    c = c & ~0x02;
    c = c & ~0x18;
    c = c | (uint8_t)(Gscale << 3);
    writeByte(MPU9250_ADDRESS, GYRO_CONFIG, c);

    // Accel config
    c = readByte(MPU9250_ADDRESS, ACCEL_CONFIG);
    c = c & ~0x18;
    c = c | (uint8_t)(Ascale << 3);
    writeByte(MPU9250_ADDRESS, ACCEL_CONFIG, c);

    // Accel DLPF
    c = readByte(MPU9250_ADDRESS, ACCEL_CONFIG2);
    c = c & ~0x0F;
    c = c | 0x03;
    writeByte(MPU9250_ADDRESS, ACCEL_CONFIG2, c);

    writeByte(MPU9250_ADDRESS, INT_PIN_CFG, 0x22);
    writeByte(MPU9250_ADDRESS, INT_ENABLE, 0x01);
}

// ─────────────────────────────────────────────
// Calibration (FIFO based — more accurate)
// ─────────────────────────────────────────────

void MPU9250::calibrateMPU9250(float *dest1, float *dest2) {
    uint8_t data[12];
    uint16_t packet_count, fifo_count;
    int32_t gyro_bias[3] = {0, 0, 0}, accel_bias[3] = {0, 0, 0};

    // Reset device
    writeByte(MPU9250_ADDRESS, PWR_MGMT_1, 0x80);
    HAL_Delay(100);  // mbed: wait(0.1)

    writeByte(MPU9250_ADDRESS, PWR_MGMT_1, 0x01);
    writeByte(MPU9250_ADDRESS, PWR_MGMT_2, 0x00);
    HAL_Delay(200);  // mbed: wait(0.2)

    // Disable interrupts and FIFO
    writeByte(MPU9250_ADDRESS, INT_ENABLE, 0x00);
    writeByte(MPU9250_ADDRESS, FIFO_EN, 0x00);
    writeByte(MPU9250_ADDRESS, PWR_MGMT_1, 0x00);
    writeByte(MPU9250_ADDRESS, I2C_MST_CTRL, 0x00);
    writeByte(MPU9250_ADDRESS, USER_CTRL, 0x00);
    writeByte(MPU9250_ADDRESS, USER_CTRL, 0x0C);
    HAL_Delay(15);   // mbed: wait(0.015)

    // Configure for calibration
    writeByte(MPU9250_ADDRESS, CONFIG, 0x01);
    writeByte(MPU9250_ADDRESS, SMPLRT_DIV, 0x00);
    writeByte(MPU9250_ADDRESS, GYRO_CONFIG, 0x00);
    writeByte(MPU9250_ADDRESS, ACCEL_CONFIG, 0x00);

    uint16_t gyrosensitivity  = 131;
    uint16_t accelsensitivity = 16384;

    // Enable FIFO
    writeByte(MPU9250_ADDRESS, USER_CTRL, 0x40);
    writeByte(MPU9250_ADDRESS, FIFO_EN, 0x78);
    HAL_Delay(40);   // mbed: wait(0.04)

    // Read FIFO sample count
    writeByte(MPU9250_ADDRESS, FIFO_EN, 0x00);
    readBytes(MPU9250_ADDRESS, FIFO_COUNTH, 2, &data[0]);
    fifo_count = ((uint16_t)data[0] << 8) | data[1];
    packet_count = fifo_count / 12;

    for (uint16_t ii = 0; ii < packet_count; ii++) {
        int16_t accel_temp[3] = {0}, gyro_temp[3] = {0};
        readBytes(MPU9250_ADDRESS, FIFO_R_W, 12, &data[0]);
        accel_temp[0] = (int16_t)(((int16_t)data[0]  << 8) | data[1]);
        accel_temp[1] = (int16_t)(((int16_t)data[2]  << 8) | data[3]);
        accel_temp[2] = (int16_t)(((int16_t)data[4]  << 8) | data[5]);
        gyro_temp[0]  = (int16_t)(((int16_t)data[6]  << 8) | data[7]);
        gyro_temp[1]  = (int16_t)(((int16_t)data[8]  << 8) | data[9]);
        gyro_temp[2]  = (int16_t)(((int16_t)data[10] << 8) | data[11]);
        accel_bias[0] += (int32_t)accel_temp[0];
        accel_bias[1] += (int32_t)accel_temp[1];
        accel_bias[2] += (int32_t)accel_temp[2];
        gyro_bias[0]  += (int32_t)gyro_temp[0];
        gyro_bias[1]  += (int32_t)gyro_temp[1];
        gyro_bias[2]  += (int32_t)gyro_temp[2];
    }

    accel_bias[0] /= (int32_t)packet_count;
    accel_bias[1] /= (int32_t)packet_count;
    accel_bias[2] /= (int32_t)packet_count;
    gyro_bias[0]  /= (int32_t)packet_count;
    gyro_bias[1]  /= (int32_t)packet_count;
    gyro_bias[2]  /= (int32_t)packet_count;

    if (accel_bias[2] > 0L) accel_bias[2] -= (int32_t)accelsensitivity;
    else                     accel_bias[2] += (int32_t)accelsensitivity;

    // Gyro biases
    dest1[0] = (float)gyro_bias[0] / (float)gyrosensitivity;
    dest1[1] = (float)gyro_bias[1] / (float)gyrosensitivity;
    dest1[2] = (float)gyro_bias[2] / (float)gyrosensitivity;

    // Accel biases — read factory trim and subtract
    int32_t accel_bias_reg[3] = {0};
    readBytes(MPU9250_ADDRESS, XA_OFFSET_H, 2, &data[0]);
    accel_bias_reg[0] = (int16_t)((int16_t)data[0] << 8) | data[1];
    readBytes(MPU9250_ADDRESS, YA_OFFSET_H, 2, &data[0]);
    accel_bias_reg[1] = (int16_t)((int16_t)data[0] << 8) | data[1];
    readBytes(MPU9250_ADDRESS, ZA_OFFSET_H, 2, &data[0]);
    accel_bias_reg[2] = (int16_t)((int16_t)data[0] << 8) | data[1];

    uint32_t mask = 1uL;
    uint8_t mask_bit[3] = {0, 0, 0};
    for (int ii = 0; ii < 3; ii++) {
        if (accel_bias_reg[ii] & mask) mask_bit[ii] = 0x01;
    }

    accel_bias_reg[0] -= (accel_bias[0] / 8);
    accel_bias_reg[1] -= (accel_bias[1] / 8);
    accel_bias_reg[2] -= (accel_bias[2] / 8);

    data[0] = (accel_bias_reg[0] >> 8) & 0xFF;
    data[1] = (accel_bias_reg[0])      & 0xFF;
    data[1] = data[1] | mask_bit[0];
    data[2] = (accel_bias_reg[1] >> 8) & 0xFF;
    data[3] = (accel_bias_reg[1])      & 0xFF;
    data[3] = data[3] | mask_bit[1];
    data[4] = (accel_bias_reg[2] >> 8) & 0xFF;
    data[5] = (accel_bias_reg[2])      & 0xFF;
    data[5] = data[5] | mask_bit[2];

    dest2[0] = (float)accel_bias[0] / (float)accelsensitivity;
    dest2[1] = (float)accel_bias[1] / (float)accelsensitivity;
    dest2[2] = (float)accel_bias[2] / (float)accelsensitivity;
}

// ─────────────────────────────────────────────
// Self Test
// ─────────────────────────────────────────────

void MPU9250::selfTest(float *destination) {
    uint8_t rawData[6] = {0};
    uint8_t selfTestData[6];
    int32_t gAvg[3] = {0}, aAvg[3] = {0}, aSTAvg[3] = {0}, gSTAvg[3] = {0};
    float factoryTrim[6];
    uint8_t FS = 0;

    writeByte(MPU9250_ADDRESS, SMPLRT_DIV, 0x00);
    writeByte(MPU9250_ADDRESS, CONFIG, 0x02);
    writeByte(MPU9250_ADDRESS, GYRO_CONFIG, FS << 3);
    writeByte(MPU9250_ADDRESS, ACCEL_CONFIG2, 0x02);
    writeByte(MPU9250_ADDRESS, ACCEL_CONFIG, FS << 3);

    for (int ii = 0; ii < 200; ii++) {
        readBytes(MPU9250_ADDRESS, ACCEL_XOUT_H, 6, rawData);
        aAvg[0] += (int16_t)(((int16_t)rawData[0] << 8) | rawData[1]);
        aAvg[1] += (int16_t)(((int16_t)rawData[2] << 8) | rawData[3]);
        aAvg[2] += (int16_t)(((int16_t)rawData[4] << 8) | rawData[5]);
        readBytes(MPU9250_ADDRESS, GYRO_XOUT_H, 6, rawData);
        gAvg[0] += (int16_t)(((int16_t)rawData[0] << 8) | rawData[1]);
        gAvg[1] += (int16_t)(((int16_t)rawData[2] << 8) | rawData[3]);
        gAvg[2] += (int16_t)(((int16_t)rawData[4] << 8) | rawData[5]);
    }
    for (int ii = 0; ii < 3; ii++) { aAvg[ii] /= 200; gAvg[ii] /= 200; }

    writeByte(MPU9250_ADDRESS, ACCEL_CONFIG, 0xE0);
    writeByte(MPU9250_ADDRESS, GYRO_CONFIG, 0xE0);
    HAL_Delay(25);  // mbed: delay(25)

    for (int ii = 0; ii < 200; ii++) {
        readBytes(MPU9250_ADDRESS, ACCEL_XOUT_H, 6, rawData);
        aSTAvg[0] += (int16_t)(((int16_t)rawData[0] << 8) | rawData[1]);
        aSTAvg[1] += (int16_t)(((int16_t)rawData[2] << 8) | rawData[3]);
        aSTAvg[2] += (int16_t)(((int16_t)rawData[4] << 8) | rawData[5]);
        readBytes(MPU9250_ADDRESS, GYRO_XOUT_H, 6, rawData);
        gSTAvg[0] += (int16_t)(((int16_t)rawData[0] << 8) | rawData[1]);
        gSTAvg[1] += (int16_t)(((int16_t)rawData[2] << 8) | rawData[3]);
        gSTAvg[2] += (int16_t)(((int16_t)rawData[4] << 8) | rawData[5]);
    }
    for (int ii = 0; ii < 3; ii++) { aSTAvg[ii] /= 200; gSTAvg[ii] /= 200; }

    writeByte(MPU9250_ADDRESS, ACCEL_CONFIG, 0x00);
    writeByte(MPU9250_ADDRESS, GYRO_CONFIG, 0x00);
    HAL_Delay(25);

    selfTestData[0] = readByte(MPU9250_ADDRESS, SELF_TEST_X_ACCEL);
    selfTestData[1] = readByte(MPU9250_ADDRESS, SELF_TEST_Y_ACCEL);
    selfTestData[2] = readByte(MPU9250_ADDRESS, SELF_TEST_Z_ACCEL);
    selfTestData[3] = readByte(MPU9250_ADDRESS, SELF_TEST_X_GYRO);
    selfTestData[4] = readByte(MPU9250_ADDRESS, SELF_TEST_Y_GYRO);
    selfTestData[5] = readByte(MPU9250_ADDRESS, SELF_TEST_Z_GYRO);

    for (int i = 0; i < 6; i++) {
        factoryTrim[i] = (float)(2620 / (1 << FS)) * powf(1.01f, (float)selfTestData[i] - 1.0f);
    }

    for (int i = 0; i < 3; i++) {
        destination[i]   = 100.0f * (float)(aSTAvg[i] - aAvg[i]) / factoryTrim[i]   - 100.0f;
        destination[i+3] = 100.0f * (float)(gSTAvg[i] - gAvg[i]) / factoryTrim[i+3] - 100.0f;
    }
}

void MPU9250::saveCalibration(CalibrationData &data) {
    data.calibration_status = 0x01;  // mark as valid

    HAL_FLASH_Unlock();

    FLASH_EraseInitTypeDef EraseInitStruct;
    uint32_t SectorError;

    EraseInitStruct.TypeErase = FLASH_TYPEERASE_SECTORS;
    EraseInitStruct.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    EraseInitStruct.Sector = FLASH_SECTOR_5;
    EraseInitStruct.NbSectors = 1;

    if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
        HAL_FLASH_Lock();
        return;
    }

    // write struct word by word
    uint32_t *ptr = (uint32_t*)&data;
    for (int i = 0; i < sizeof(CalibrationData) / 4; i++) {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, flash_address + i * 4, ptr[i]) != HAL_OK) {
            HAL_FLASH_Lock();
            return;
        }
    }

    HAL_FLASH_Lock();
}

bool MPU9250::loadCalibration(CalibrationData &data) {
    memcpy(&data, reinterpret_cast<void*>(flash_address), sizeof(CalibrationData));
    if (data.calibration_status == 0x01) {
        accelBias[0] = data.acc_offset_x;
        accelBias[1] = data.acc_offset_y;
        accelBias[2] = data.acc_offset_z;
        gyroBias[0]  = data.gyr_offset_x;
        gyroBias[1]  = data.gyr_offset_y;
        gyroBias[2]  = data.gyr_offset_z;
        magbias[0] = data.mag_offset_x;
        magbias[1] = data.mag_offset_y;
        magbias[2] = data.mag_offset_z;
        return true;
    }
    return false;
}

void MPU9250::MadgwickQuaternionUpdate(float ax, float ay, float az, float gx, float gy, float gz, float mx, float my, float mz)
        {
            float q1 = q[0], q2 = q[1], q3 = q[2], q4 = q[3];   // short name local variable for readability
            float norm;
            float hx, hy, _2bx, _2bz;
            float s1, s2, s3, s4;
            float qDot1, qDot2, qDot3, qDot4;

            // Auxiliary variables to avoid repeated arithmetic
            float _2q1mx;
            float _2q1my;
            float _2q1mz;
            float _2q2mx;
            float _4bx;
            float _4bz;
            float _2q1 = 2.0f * q1;
            float _2q2 = 2.0f * q2;
            float _2q3 = 2.0f * q3;
            float _2q4 = 2.0f * q4;
            float _2q1q3 = 2.0f * q1 * q3;
            float _2q3q4 = 2.0f * q3 * q4;
            float q1q1 = q1 * q1;
            float q1q2 = q1 * q2;
            float q1q3 = q1 * q3;
            float q1q4 = q1 * q4;
            float q2q2 = q2 * q2;
            float q2q3 = q2 * q3;
            float q2q4 = q2 * q4;
            float q3q3 = q3 * q3;
            float q3q4 = q3 * q4;
            float q4q4 = q4 * q4;

            // Normalise accelerometer measurement
            norm = sqrt(ax * ax + ay * ay + az * az);
            if (norm == 0.0f) return; // handle NaN
            norm = 1.0f/norm;
            ax *= norm;
            ay *= norm;
            az *= norm;

            // Normalise magnetometer measurement
            norm = sqrt(mx * mx + my * my + mz * mz);
            if (norm == 0.0f) return; // handle NaN
            norm = 1.0f/norm;
            mx *= norm;
            my *= norm;
            mz *= norm;

            // Reference direction of Earth's magnetic field
            _2q1mx = 2.0f * q1 * mx;
            _2q1my = 2.0f * q1 * my;
            _2q1mz = 2.0f * q1 * mz;
            _2q2mx = 2.0f * q2 * mx;
            hx = mx * q1q1 - _2q1my * q4 + _2q1mz * q3 + mx * q2q2 + _2q2 * my * q3 + _2q2 * mz * q4 - mx * q3q3 - mx * q4q4;
            hy = _2q1mx * q4 + my * q1q1 - _2q1mz * q2 + _2q2mx * q3 - my * q2q2 + my * q3q3 + _2q3 * mz * q4 - my * q4q4;
            _2bx = sqrt(hx * hx + hy * hy);
            _2bz = -_2q1mx * q3 + _2q1my * q2 + mz * q1q1 + _2q2mx * q4 - mz * q2q2 + _2q3 * my * q4 - mz * q3q3 + mz * q4q4;
            _4bx = 2.0f * _2bx;
            _4bz = 2.0f * _2bz;

            // Gradient decent algorithm corrective step
            s1 = -_2q3 * (2.0f * q2q4 - _2q1q3 - ax) + _2q2 * (2.0f * q1q2 + _2q3q4 - ay) - _2bz * q3 * (_2bx * (0.5f - q3q3 - q4q4) + _2bz * (q2q4 - q1q3) - mx) + (-_2bx * q4 + _2bz * q2) * (_2bx * (q2q3 - q1q4) + _2bz * (q1q2 + q3q4) - my) + _2bx * q3 * (_2bx * (q1q3 + q2q4) + _2bz * (0.5f - q2q2 - q3q3) - mz);
            s2 = _2q4 * (2.0f * q2q4 - _2q1q3 - ax) + _2q1 * (2.0f * q1q2 + _2q3q4 - ay) - 4.0f * q2 * (1.0f - 2.0f * q2q2 - 2.0f * q3q3 - az) + _2bz * q4 * (_2bx * (0.5f - q3q3 - q4q4) + _2bz * (q2q4 - q1q3) - mx) + (_2bx * q3 + _2bz * q1) * (_2bx * (q2q3 - q1q4) + _2bz * (q1q2 + q3q4) - my) + (_2bx * q4 - _4bz * q2) * (_2bx * (q1q3 + q2q4) + _2bz * (0.5f - q2q2 - q3q3) - mz);
            s3 = -_2q1 * (2.0f * q2q4 - _2q1q3 - ax) + _2q4 * (2.0f * q1q2 + _2q3q4 - ay) - 4.0f * q3 * (1.0f - 2.0f * q2q2 - 2.0f * q3q3 - az) + (-_4bx * q3 - _2bz * q1) * (_2bx * (0.5f - q3q3 - q4q4) + _2bz * (q2q4 - q1q3) - mx) + (_2bx * q2 + _2bz * q4) * (_2bx * (q2q3 - q1q4) + _2bz * (q1q2 + q3q4) - my) + (_2bx * q1 - _4bz * q3) * (_2bx * (q1q3 + q2q4) + _2bz * (0.5f - q2q2 - q3q3) - mz);
            s4 = _2q2 * (2.0f * q2q4 - _2q1q3 - ax) + _2q3 * (2.0f * q1q2 + _2q3q4 - ay) + (-_4bx * q4 + _2bz * q2) * (_2bx * (0.5f - q3q3 - q4q4) + _2bz * (q2q4 - q1q3) - mx) + (-_2bx * q1 + _2bz * q3) * (_2bx * (q2q3 - q1q4) + _2bz * (q1q2 + q3q4) - my) + _2bx * q2 * (_2bx * (q1q3 + q2q4) + _2bz * (0.5f - q2q2 - q3q3) - mz);
            norm = sqrt(s1 * s1 + s2 * s2 + s3 * s3 + s4 * s4);    // normalise step magnitude
            norm = 1.0f/norm;
            s1 *= norm;
            s2 *= norm;
            s3 *= norm;
            s4 *= norm;

            // Compute rate of change of quaternion
            qDot1 = 0.5f * (-q2 * gx - q3 * gy - q4 * gz) - beta * s1;
            qDot2 = 0.5f * (q1 * gx + q3 * gz - q4 * gy) - beta * s2;
            qDot3 = 0.5f * (q1 * gy - q2 * gz + q4 * gx) - beta * s3;
            qDot4 = 0.5f * (q1 * gz + q2 * gy - q3 * gx) - beta * s4;

            // Integrate to yield quaternion
            q1 += qDot1 * deltat;
            q2 += qDot2 * deltat;
            q3 += qDot3 * deltat;
            q4 += qDot4 * deltat;
            norm = sqrt(q1 * q1 + q2 * q2 + q3 * q3 + q4 * q4);    // normalise quaternion
            norm = 1.0f/norm;
            q[0] = q1 * norm;
            q[1] = q2 * norm;
            q[2] = q3 * norm;
            q[3] = q4 * norm;

        }
//
// void MPU9250::MadgwickQuaternionUpdate(float ax, float ay, float az, float gx, float gy, float gz, float mx, float my, float mz)
// {
//     float q1 = q[0], q2 = q[1], q3 = q[2], q4 = q[3];
//     float norm;
//     float s1, s2, s3, s4;
//     float qDot1, qDot2, qDot3, qDot4;
//
//     // Auxiliary variables
//     float _2q1 = 2.0f * q1, _2q2 = 2.0f * q2;
//     float _2q3 = 2.0f * q3, _2q4 = 2.0f * q4;
//     float _4q1 = 4.0f * q1, _4q2 = 4.0f * q2, _4q3 = 4.0f * q3;
//     float _8q2 = 8.0f * q2, _8q3 = 8.0f * q3;
//     float q1q1 = q1*q1, q2q2 = q2*q2, q3q3 = q3*q3, q4q4 = q4*q4;
//
//     // Normalise accelerometer
//     norm = sqrt(ax*ax + ay*ay + az*az);
//     if (norm == 0.0f) return;
//     norm = 1.0f / norm;
//     ax *= norm; ay *= norm; az *= norm;
//
//     // Gradient descent - accel only (6DOF)
//     s1 = _4q1*q3q3 + _2q3*ax + _4q1*q2q2 - _2q2*ay;
//     s2 = _4q2*q4q4 - _2q4*ax + 4.0f*q1q1*q2 - _2q1*ay - _4q2 + _8q2*q2q2 + _8q2*q3q3 + _4q2*az;
//     s3 = 4.0f*q1q1*q3 + _2q1*ax + _4q3*q4q4 - _2q4*ay - _4q3 + _8q3*q2q2 + _8q3*q3q3 + _4q3*az;
//     s4 = 4.0f*q2q2*q4 - _2q2*ax + 4.0f*q3q3*q4 - _2q3*ay;
//
//     norm = sqrt(s1*s1 + s2*s2 + s3*s3 + s4*s4);
//     norm = 1.0f / norm;
//     s1 *= norm; s2 *= norm; s3 *= norm; s4 *= norm;
//
//     // Rate of change of quaternion
//     qDot1 = 0.5f*(-q2*gx - q3*gy - q4*gz) - beta*s1;
//     qDot2 = 0.5f*(q1*gx + q3*gz - q4*gy)  - beta*s2;
//     qDot3 = 0.5f*(q1*gy - q2*gz + q4*gx)  - beta*s3;
//     qDot4 = 0.5f*(q1*gz + q2*gy - q3*gx)  - beta*s4;
//
//     // Integrate
//     q1 += qDot1 * deltat;
//     q2 += qDot2 * deltat;
//     q3 += qDot3 * deltat;
//     q4 += qDot4 * deltat;
//
//     norm = sqrt(q1*q1 + q2*q2 + q3*q3 + q4*q4);
//     norm = 1.0f / norm;
//     q[0] = q1*norm; q[1] = q2*norm;
//     q[2] = q3*norm; q[3] = q4*norm;
// }


 // Similar to Madgwick scheme but uses proportional and integral filtering on the error between estimated reference vectors and
 // measured ones.
void MPU9250::MahonyQuaternionUpdate(float ax, float ay, float az, float gx, float gy, float gz, float mx, float my, float mz)
        {
            float q1 = q[0], q2 = q[1], q3 = q[2], q4 = q[3];   // short name local variable for readability
            float norm;
            float hx, hy, bx, bz;
            float vx, vy, vz, wx, wy, wz;
            float ex, ey, ez;
            float pa, pb, pc;

            // Auxiliary variables to avoid repeated arithmetic
            float q1q1 = q1 * q1;
            float q1q2 = q1 * q2;
            float q1q3 = q1 * q3;
            float q1q4 = q1 * q4;
            float q2q2 = q2 * q2;
            float q2q3 = q2 * q3;
            float q2q4 = q2 * q4;
            float q3q3 = q3 * q3;
            float q3q4 = q3 * q4;
            float q4q4 = q4 * q4;

            // Normalise accelerometer measurement
            norm = sqrt(ax * ax + ay * ay + az * az);
            if (norm == 0.0f) return; // handle NaN
            norm = 1.0f / norm;        // use reciprocal for division
            ax *= norm;
            ay *= norm;
            az *= norm;

            // Normalise magnetometer measurement
            norm = sqrt(mx * mx + my * my + mz * mz);
            if (norm == 0.0f) return; // handle NaN
            norm = 1.0f / norm;        // use reciprocal for division
            mx *= norm;
            my *= norm;
            mz *= norm;

            // Reference direction of Earth's magnetic field
            hx = 2.0f * mx * (0.5f - q3q3 - q4q4) + 2.0f * my * (q2q3 - q1q4) + 2.0f * mz * (q2q4 + q1q3);
            hy = 2.0f * mx * (q2q3 + q1q4) + 2.0f * my * (0.5f - q2q2 - q4q4) + 2.0f * mz * (q3q4 - q1q2);
            bx = sqrt((hx * hx) + (hy * hy));
            bz = 2.0f * mx * (q2q4 - q1q3) + 2.0f * my * (q3q4 + q1q2) + 2.0f * mz * (0.5f - q2q2 - q3q3);

            // Estimated direction of gravity and magnetic field
            vx = 2.0f * (q2q4 - q1q3);
            vy = 2.0f * (q1q2 + q3q4);
            vz = q1q1 - q2q2 - q3q3 + q4q4;
            wx = 2.0f * bx * (0.5f - q3q3 - q4q4) + 2.0f * bz * (q2q4 - q1q3);
            wy = 2.0f * bx * (q2q3 - q1q4) + 2.0f * bz * (q1q2 + q3q4);
            wz = 2.0f * bx * (q1q3 + q2q4) + 2.0f * bz * (0.5f - q2q2 - q3q3);

            // Error is cross product between estimated direction and measured direction of gravity
            ex = (ay * vz - az * vy) + (my * wz - mz * wy);
            ey = (az * vx - ax * vz) + (mz * wx - mx * wz);
            ez = (ax * vy - ay * vx) + (mx * wy - my * wx);
            if (Ki > 0.0f)
            {
                eInt[0] += ex;      // accumulate integral error
                eInt[1] += ey;
                eInt[2] += ez;
            }
            else
            {
                eInt[0] = 0.0f;     // prevent integral wind up
                eInt[1] = 0.0f;
                eInt[2] = 0.0f;
            }

            // Apply feedback terms
            gx = gx + Kp * ex + Ki * eInt[0];
            gy = gy + Kp * ey + Ki * eInt[1];
            gz = gz + Kp * ez + Ki * eInt[2];

            // Integrate rate of change of quaternion
            pa = q2;
            pb = q3;
            pc = q4;
            q1 = q1 + (-q2 * gx - q3 * gy - q4 * gz) * (0.5f * deltat);
            q2 = pa + (q1 * gx + pb * gz - pc * gy) * (0.5f * deltat);
            q3 = pb + (q1 * gy - pa * gz + pc * gx) * (0.5f * deltat);
            q4 = pc + (q1 * gz + pa * gy - pb * gx) * (0.5f * deltat);

            // Normalise quaternion
            norm = sqrt(q1 * q1 + q2 * q2 + q3 * q3 + q4 * q4);
            norm = 1.0f / norm;
            q[0] = q1 * norm;
            q[1] = q2 * norm;
            q[2] = q3 * norm;
            q[3] = q4 * norm;

        }

vec_3 MPU9250::getEulerAngles() {
    vec_3 angles;
    float q0 = q[0], q1 = q[1], q2 = q[2], q3 = q[3];

    // yaw 0 to 360
    angles.z() = atan2f(2.0f*(q1*q2 + q0*q3),
                        q0*q0 + q1*q1 - q2*q2 - q3*q3) * 180.0f / PI;
    if (angles.z() < 0) angles.z() += 360.0f;

    // pitch -180 to 180
    angles.y() = -asinf(2.0f*(q1*q3 - q0*q2)) * 180.0f / PI;

    // roll -90 to 90
    angles.x() = atan2f(2.0f*(q0*q1 + q2*q3),
                         q0*q0 - q1*q1 - q2*q2 + q3*q3) * 180.0f / PI;
    return angles;
}

vec_3 MPU9250::getBodyRates() {
    int16_t gyroCount[3];
    readGyroData(gyroCount);
    vec_3 rates;
    rates.x() = (float)gyroCount[0] * gRes - gyroBias[0];
    rates.y() = (float)gyroCount[1] * gRes - gyroBias[1];
    rates.z() = (float)gyroCount[2] * gRes - gyroBias[2];
    return rates;
}