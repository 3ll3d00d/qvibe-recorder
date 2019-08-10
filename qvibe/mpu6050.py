import collections
import logging
import struct
from _ctypes import ArgumentError
from time import sleep, time

from qvibe.accelerometer import Accelerometer, ACCEL_X, ACCEL_Y, ACCEL_Z, GYRO_X, GYRO_Y, GYRO_Z, TEMP, SAMPLE_IDX, FS,\
    NAME, ZERO_TIME

SENSOR_SCALE_FACTOR = 32768.0
DEFAULT_GYRO_SENSITIVITY = 500.0
DEFAULT_ACCELEROMETER_SENSITIVITY = 2.0
DEFAULT_TEMPERATURE_GAIN = 1.0 / 340.0
DEFAULT_TEMPERATURE_OFFSET = 36.53

logger = logging.getLogger(__name__)


class mpu6050(Accelerometer):
    """
    Controls the Invensense MPU-6050, code based on danjperron's https://github.com/danjperron/mpu6050TestInC
    """
    # Temperature in degrees C = (TEMP_OUT Register Value as a signed quantity)/340 + 36.53
    _temperatureGain = DEFAULT_TEMPERATURE_GAIN
    _temperatureOffset = DEFAULT_TEMPERATURE_OFFSET

    # converted from Jeff Rowberg code https://github.com/jrowberg/i2cdevlib/blob/master/Arduino/MPU6050/MPU6050.h
    MPU6050_ADDRESS = 0x68  # default I2C Address

    # bit masks for enabling the which sensors are written to the FIFO
    enable_accelerometer_mask = 0b00001000
    enableGyroMask = 0b01110000
    enableTemperatureMask = 0b10000000

    # register definition
    MPU6050_RA_XG_OFFS_TC = 0x00  # [7] PWR_MODE, [6:1] XG_OFFS_TC, [0] OTP_BNK_VLD
    MPU6050_RA_YG_OFFS_TC = 0x01  # [7] PWR_MODE, [6:1] YG_OFFS_TC, [0] OTP_BNK_VLD
    MPU6050_RA_ZG_OFFS_TC = 0x02  # [7] PWR_MODE, [6:1] ZG_OFFS_TC, [0] OTP_BNK_VLD
    MPU6050_RA_X_FINE_GAIN = 0x03  # [7:0] X_FINE_GAIN
    MPU6050_RA_Y_FINE_GAIN = 0x04  # [7:0] Y_FINE_GAIN
    MPU6050_RA_Z_FINE_GAIN = 0x05  # [7:0] Z_FINE_GAIN
    MPU6050_RA_XA_OFFS_H = 0x06  # [15:0] XA_OFFS
    MPU6050_RA_XA_OFFS_L_TC = 0x07
    MPU6050_RA_YA_OFFS_H = 0x08  # [15:0] YA_OFFS
    MPU6050_RA_YA_OFFS_L_TC = 0x09
    MPU6050_RA_ZA_OFFS_H = 0x0A  # [15:0] ZA_OFFS
    MPU6050_RA_ZA_OFFS_L_TC = 0x0B
    MPU6050_RA_XG_OFFS_USRH = 0x13  # [15:0] XG_OFFS_USR
    MPU6050_RA_XG_OFFS_USRL = 0x14
    MPU6050_RA_YG_OFFS_USRH = 0x15  # [15:0] YG_OFFS_USR
    MPU6050_RA_YG_OFFS_USRL = 0x16
    MPU6050_RA_ZG_OFFS_USRH = 0x17  # [15:0] ZG_OFFS_USR
    MPU6050_RA_ZG_OFFS_USRL = 0x18
    MPU6050_RA_SMPLRT_DIV = 0x19
    MPU6050_RA_CONFIG = 0x1A
    MPU6050_RA_GYRO_CONFIG = 0x1B
    MPU6050_RA_ACCEL_CONFIG = 0x1C
    MPU6050_RA_FF_THR = 0x1D
    MPU6050_RA_FF_DUR = 0x1E
    MPU6050_RA_MOT_THR = 0x1F
    MPU6050_RA_MOT_DUR = 0x20
    MPU6050_RA_ZRMOT_THR = 0x21
    MPU6050_RA_ZRMOT_DUR = 0x22
    MPU6050_RA_FIFO_EN = 0x23
    MPU6050_RA_I2C_MST_CTRL = 0x24
    MPU6050_RA_I2C_SLV0_ADDR = 0x25
    MPU6050_RA_I2C_SLV0_REG = 0x26
    MPU6050_RA_I2C_SLV0_CTRL = 0x27
    MPU6050_RA_I2C_SLV1_ADDR = 0x28
    MPU6050_RA_I2C_SLV1_REG = 0x29
    MPU6050_RA_I2C_SLV1_CTRL = 0x2A
    MPU6050_RA_I2C_SLV2_ADDR = 0x2B
    MPU6050_RA_I2C_SLV2_REG = 0x2C
    MPU6050_RA_I2C_SLV2_CTRL = 0x2D
    MPU6050_RA_I2C_SLV3_ADDR = 0x2E
    MPU6050_RA_I2C_SLV3_REG = 0x2F
    MPU6050_RA_I2C_SLV3_CTRL = 0x30
    MPU6050_RA_I2C_SLV4_ADDR = 0x31
    MPU6050_RA_I2C_SLV4_REG = 0x32
    MPU6050_RA_I2C_SLV4_DO = 0x33
    MPU6050_RA_I2C_SLV4_CTRL = 0x34
    MPU6050_RA_I2C_SLV4_DI = 0x35
    MPU6050_RA_I2C_MST_STATUS = 0x36
    MPU6050_RA_INT_PIN_CFG = 0x37
    MPU6050_RA_INT_ENABLE = 0x38
    MPU6050_RA_DMP_INT_STATUS = 0x39
    MPU6050_RA_INT_STATUS = 0x3A
    MPU6050_RA_ACCEL_XOUT_H = 0x3B
    MPU6050_RA_ACCEL_XOUT_L = 0x3C
    MPU6050_RA_ACCEL_YOUT_H = 0x3D
    MPU6050_RA_ACCEL_YOUT_L = 0x3E
    MPU6050_RA_ACCEL_ZOUT_H = 0x3F
    MPU6050_RA_ACCEL_ZOUT_L = 0x40
    MPU6050_RA_TEMP_OUT_H = 0x41
    MPU6050_RA_TEMP_OUT_L = 0x42
    MPU6050_RA_GYRO_XOUT_H = 0x43
    MPU6050_RA_GYRO_XOUT_L = 0x44
    MPU6050_RA_GYRO_YOUT_H = 0x45
    MPU6050_RA_GYRO_YOUT_L = 0x46
    MPU6050_RA_GYRO_ZOUT_H = 0x47
    MPU6050_RA_GYRO_ZOUT_L = 0x48
    MPU6050_RA_EXT_SENS_DATA_00 = 0x49
    MPU6050_RA_EXT_SENS_DATA_01 = 0x4A
    MPU6050_RA_EXT_SENS_DATA_02 = 0x4B
    MPU6050_RA_EXT_SENS_DATA_03 = 0x4C
    MPU6050_RA_EXT_SENS_DATA_04 = 0x4D
    MPU6050_RA_EXT_SENS_DATA_05 = 0x4E
    MPU6050_RA_EXT_SENS_DATA_06 = 0x4F
    MPU6050_RA_EXT_SENS_DATA_07 = 0x50
    MPU6050_RA_EXT_SENS_DATA_08 = 0x51
    MPU6050_RA_EXT_SENS_DATA_09 = 0x52
    MPU6050_RA_EXT_SENS_DATA_10 = 0x53
    MPU6050_RA_EXT_SENS_DATA_11 = 0x54
    MPU6050_RA_EXT_SENS_DATA_12 = 0x55
    MPU6050_RA_EXT_SENS_DATA_13 = 0x56
    MPU6050_RA_EXT_SENS_DATA_14 = 0x57
    MPU6050_RA_EXT_SENS_DATA_15 = 0x58
    MPU6050_RA_EXT_SENS_DATA_16 = 0x59
    MPU6050_RA_EXT_SENS_DATA_17 = 0x5A
    MPU6050_RA_EXT_SENS_DATA_18 = 0x5B
    MPU6050_RA_EXT_SENS_DATA_19 = 0x5C
    MPU6050_RA_EXT_SENS_DATA_20 = 0x5D
    MPU6050_RA_EXT_SENS_DATA_21 = 0x5E
    MPU6050_RA_EXT_SENS_DATA_22 = 0x5F
    MPU6050_RA_EXT_SENS_DATA_23 = 0x60
    MPU6050_RA_MOT_DETECT_STATUS = 0x61
    MPU6050_RA_I2C_SLV0_DO = 0x63
    MPU6050_RA_I2C_SLV1_DO = 0x64
    MPU6050_RA_I2C_SLV2_DO = 0x65
    MPU6050_RA_I2C_SLV3_DO = 0x66
    MPU6050_RA_I2C_MST_DELAY_CTRL = 0x67
    MPU6050_RA_SIGNAL_PATH_RESET = 0x68
    MPU6050_RA_MOT_DETECT_CTRL = 0x69
    MPU6050_RA_USER_CTRL = 0x6A
    MPU6050_RA_PWR_MGMT_1 = 0x6B
    MPU6050_RA_PWR_MGMT_2 = 0x6C
    MPU6050_RA_BANK_SEL = 0x6D
    MPU6050_RA_MEM_START_ADDR = 0x6E
    MPU6050_RA_MEM_R_W = 0x6F
    MPU6050_RA_DMP_CFG_1 = 0x70
    MPU6050_RA_DMP_CFG_2 = 0x71
    MPU6050_RA_FIFO_COUNTH = 0x72
    MPU6050_RA_FIFO_COUNTL = 0x73
    MPU6050_RA_FIFO_R_W = 0x74
    MPU6050_RA_WHO_AM_I = 0x75

    ZeroRegister = [
        MPU6050_RA_FF_THR,  # Freefall threshold of |0mg|  LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_FF_THR, 0x00);
        MPU6050_RA_FF_DUR,  # Freefall duration limit of 0   LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_FF_DUR, 0x00);
        MPU6050_RA_MOT_THR,  # Motion threshold of 0mg     LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_MOT_THR, 0x00);
        MPU6050_RA_MOT_DUR,  # Motion duration of 0s    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_MOT_DUR, 0x00);
        MPU6050_RA_ZRMOT_THR,  # Zero motion threshold    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_ZRMOT_THR, 0x00);
        MPU6050_RA_ZRMOT_DUR,
        # Zero motion duration threshold    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_ZRMOT_DUR, 0x00);
        MPU6050_RA_FIFO_EN,
        # Disable sensor output to FIFO buffer    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_FIFO_EN, 0x00);
        MPU6050_RA_I2C_MST_CTRL,
        # AUX I2C setup    //Sets AUX I2C to single master control, plus other config    LDByteWriteI2C(
        # MPU6050_ADDRESS, MPU6050_RA_I2C_MST_CTRL, 0x00);
        MPU6050_RA_I2C_SLV0_ADDR,
        # Setup AUX I2C slaves    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_ADDR, 0x00);
        MPU6050_RA_I2C_SLV0_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_REG, 0x00);
        MPU6050_RA_I2C_SLV0_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_CTRL, 0x00);
        MPU6050_RA_I2C_SLV1_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_ADDR, 0x00);
        MPU6050_RA_I2C_SLV1_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_REG, 0x00);
        MPU6050_RA_I2C_SLV1_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_CTRL, 0x00);
        MPU6050_RA_I2C_SLV2_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_ADDR, 0x00);
        MPU6050_RA_I2C_SLV2_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_REG, 0x00);
        MPU6050_RA_I2C_SLV2_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_CTRL, 0x00);
        MPU6050_RA_I2C_SLV3_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_ADDR, 0x00);
        MPU6050_RA_I2C_SLV3_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_REG, 0x00);
        MPU6050_RA_I2C_SLV3_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_CTRL, 0x00);
        MPU6050_RA_I2C_SLV4_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_ADDR, 0x00);
        MPU6050_RA_I2C_SLV4_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_REG, 0x00);
        MPU6050_RA_I2C_SLV4_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_DO, 0x00);
        MPU6050_RA_I2C_SLV4_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_CTRL, 0x00);
        MPU6050_RA_I2C_SLV4_DI,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_DI, 0x00);
        MPU6050_RA_INT_PIN_CFG,
        # MPU6050_RA_I2C_MST_STATUS //Read-only    //Setup INT pin and AUX I2C pass through    LDByteWriteI2C(
        # MPU6050_ADDRESS, MPU6050_RA_INT_PIN_CFG, 0x00);
        MPU6050_RA_INT_ENABLE,
        # Enable data ready interrupt      LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_INT_ENABLE, 0x00);
        MPU6050_RA_I2C_SLV0_DO,
        # Slave out, dont care    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_DO, 0x00);
        MPU6050_RA_I2C_SLV1_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_DO, 0x00);
        MPU6050_RA_I2C_SLV2_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_DO, 0x00);
        MPU6050_RA_I2C_SLV3_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_DO, 0x00);
        MPU6050_RA_I2C_MST_DELAY_CTRL,
        # More slave config      LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_MST_DELAY_CTRL, 0x00);
        MPU6050_RA_SIGNAL_PATH_RESET,
        # Reset sensor signal paths    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_SIGNAL_PATH_RESET, 0x00);
        MPU6050_RA_MOT_DETECT_CTRL,
        # Motion detection control    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_MOT_DETECT_CTRL, 0x00);
        MPU6050_RA_USER_CTRL,
        # Disables FIFO, AUX I2C, FIFO and I2C reset bits to 0    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_USER_CTRL,
        #  0x00);
        MPU6050_RA_CONFIG,  # Disable FSync, 256Hz DLPF    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_CONFIG, 0x00);
        MPU6050_RA_FF_THR,  # Freefall threshold of |0mg|    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_FF_THR, 0x00);
        MPU6050_RA_FF_DUR,  # Freefall duration limit of 0    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_FF_DUR, 0x00);
        MPU6050_RA_MOT_THR,  # Motion threshold of 0mg    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_MOT_THR, 0x00);
        MPU6050_RA_MOT_DUR,  # Motion duration of 0s    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_MOT_DUR, 0x00);
        MPU6050_RA_ZRMOT_THR,  # Zero motion threshold    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_ZRMOT_THR, 0x00);
        MPU6050_RA_ZRMOT_DUR,
        # Zero motion duration threshold    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_ZRMOT_DUR, 0x00);
        MPU6050_RA_FIFO_EN,
        # Disable sensor output to FIFO buffer    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_FIFO_EN, 0x00);
        MPU6050_RA_I2C_MST_CTRL,
        # AUX I2C setup    //Sets AUX I2C to single master control, plus other config    LDByteWriteI2C(
        # MPU6050_ADDRESS, MPU6050_RA_I2C_MST_CTRL, 0x00);
        MPU6050_RA_I2C_SLV0_ADDR,
        # Setup AUX I2C slaves    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_ADDR, 0x00);
        MPU6050_RA_I2C_SLV0_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_REG, 0x00);
        MPU6050_RA_I2C_SLV0_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_CTRL, 0x00);
        MPU6050_RA_I2C_SLV1_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_ADDR, 0x00);
        MPU6050_RA_I2C_SLV1_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_REG, 0x00);
        MPU6050_RA_I2C_SLV1_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_CTRL, 0x00);
        MPU6050_RA_I2C_SLV2_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_ADDR, 0x00);
        MPU6050_RA_I2C_SLV2_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_REG, 0x00);
        MPU6050_RA_I2C_SLV2_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_CTRL, 0x00);
        MPU6050_RA_I2C_SLV3_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_ADDR, 0x00);
        MPU6050_RA_I2C_SLV3_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_REG, 0x00);
        MPU6050_RA_I2C_SLV3_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_CTRL, 0x00);
        MPU6050_RA_I2C_SLV4_ADDR,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_ADDR, 0x00);
        MPU6050_RA_I2C_SLV4_REG,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_REG, 0x00);
        MPU6050_RA_I2C_SLV4_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_DO, 0x00);
        MPU6050_RA_I2C_SLV4_CTRL,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_CTRL, 0x00);
        MPU6050_RA_I2C_SLV4_DI,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV4_DI, 0x00);
        MPU6050_RA_I2C_SLV0_DO,
        # Slave out, dont care    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV0_DO, 0x00);
        MPU6050_RA_I2C_SLV1_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV1_DO, 0x00);
        MPU6050_RA_I2C_SLV2_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV2_DO, 0x00);
        MPU6050_RA_I2C_SLV3_DO,  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_SLV3_DO, 0x00);
        MPU6050_RA_I2C_MST_DELAY_CTRL,
        # More slave config    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_I2C_MST_DELAY_CTRL, 0x00);
        MPU6050_RA_SIGNAL_PATH_RESET,
        # Reset sensor signal paths    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_SIGNAL_PATH_RESET, 0x00);
        MPU6050_RA_MOT_DETECT_CTRL,
        # Motion detection control    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_MOT_DETECT_CTRL, 0x00);
        MPU6050_RA_USER_CTRL,
        # Disables FIFO, AUX I2C, FIFO and I2C reset bits to 0    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_USER_CTRL,
        #  0x00);
        MPU6050_RA_INT_PIN_CFG,
        # MPU6050_RA_I2C_MST_STATUS //Read-only    //Setup INT pin and AUX I2C pass through    LDByteWriteI2C(
        # MPU6050_ADDRESS, MPU6050_RA_INT_PIN_CFG, 0x00);
        MPU6050_RA_INT_ENABLE,
        # Enable data ready interrupt    LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_INT_ENABLE, 0x00);
        MPU6050_RA_FIFO_R_W]  # LDByteWriteI2C(MPU6050_ADDRESS, MPU6050_RA_FIFO_R_W, 0x00);

    def __init__(self, i2c_io, fs=None, name='mpu6050', samples_per_batch=None, data_handler=None, self_test=True):
        """
        initialises to a default state set to measure acceleration only.
        """
        super().__init__(fs, samples_per_batch, data_handler)
        self.name = name
        self.fifo_sensor_mask = self.enable_accelerometer_mask
        self._accel_enabled = True
        self._gyro_enabled = False
        self._set_sample_size_bytes()
        self.accelerometer_sensitivity = DEFAULT_ACCELEROMETER_SENSITIVITY
        self.gyro_sensitivity = DEFAULT_GYRO_SENSITIVITY
        self._acceleration_factor = self.accelerometer_sensitivity / SENSOR_SCALE_FACTOR
        self._gyro_factor = self.gyro_sensitivity / SENSOR_SCALE_FACTOR
        self.i2c_io = i2c_io
        self.__sample_idx = -1
        self.__time_zero = 0
        self.__fifo_reads = 0
        self.do_init()
        if self_test is True:
            passed, results = self.perform_self_test()
        else:
            passed = False
            results = {}
        self.__self_tested = passed
        self.__self_test_results = results

    @property
    def sample_idx(self):
        return self.__sample_idx

    @sample_idx.setter
    def sample_idx(self, idx):
        self.__sample_idx = idx
        if idx == 0:
            self.__time_zero = time()

    @property
    def time_zero(self):
        return self.__time_zero

    @property
    def self_test_results(self):
        return self.__self_test_results

    @property
    def state(self):
        return {
            'name': self.name,
            'fs': self.fs,
            'sPB': self.samples_per_batch,
            'aOn': self._accel_enabled,
            'aSens': self.accelerometer_sensitivity,
            'gOn': self._gyro_enabled,
            'gSens': self.gyro_sensitivity,
            'tOn': self.is_temperature_enabled(),
            'sT': self.__self_tested
        }

    @state.setter
    def state(self, target_state):
        if 'fs' in target_state:
            if target_state['fs'] != self.fs:
                self.set_sample_rate(target_state['fs'])

        if 'sPB' in target_state:
            if target_state['sPB'] != self.samples_per_batch:
                self.samples_per_batch = target_state['sPB']
                logger.warning(f"Set samples per batch = {self.samples_per_batch}")

        if 'aOn' in target_state:
            if target_state['aOn'] and not self.is_accelerometer_enabled():
                self.enable_accelerometer()
            elif self.is_accelerometer_enabled() and not target_state['aOn']:
                self.disable_accelerometer()

        if 'aSens' in target_state:
            if target_state['aSens'] != self.accelerometer_sensitivity:
                try:
                    self.set_accelerometer_sensitivity(target_state['aSens'])
                except:
                    logger.exception("Invalid accelerometer sensitivity " + target_state['aSens'])

        if 'gOn' in target_state:
            if target_state['gOn'] and not self.is_gyro_enabled():
                self.enable_gyro()
            elif self.is_gyro_enabled() and not target_state['gOn']:
                self.disable_gyro()

        if 'gSens' in target_state:
            if target_state['gSens'] != self.gyro_sensitivity:
                try:
                    self.set_gyro_sensitivity(target_state['gSens'])
                except:
                    logger.exception("Invalid gyro sensitivity " + target_state['gSens'])

        if 'tOn' in target_state:
            if target_state['tOn'] and not self.is_temperature_enabled():
                self.enable_temperature()
            elif self.is_temperature_enabled() and not target_state['tOn']:
                self.disable_temperature()

    def _set_sample_size_bytes(self):
        """
        updates the current record of the packet size per sample and the relationship between this and the fifo reads. 
        """
        self.sample_size_bytes = self.get_packet_size()
        if self.sample_size_bytes > 0:
            self.max_bytes_per_fifo_read = (32 // self.sample_size_bytes)

    def get_packet_size(self):
        """
        the current packet size.
        :return: the current packet size based on the enabled registers.
        """
        size = 0
        if self.is_accelerometer_enabled():
            size += 6
        if self.is_gyro_enabled():
            size += 6
        if self.is_temperature_enabled():
            size += 2
        return size

    def initialise_device(self):
        """
        performs initialisation of the device
        :return:
        """
        logger.info("Initialising device")
        self.get_interrupt_status()
        self.set_accelerometer_sensitivity(self._acceleration_factor * 32768.0)
        self.set_gyro_sensitivity(self._gyro_factor * 32768.0)
        self.set_sample_rate(self.fs)
        for loop in self.ZeroRegister:
            self.i2c_io.write(self.MPU6050_ADDRESS, loop, 0)
        # Sets clock source to gyro reference w/ PLL
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_PWR_MGMT_1, 0b00000010)
        # Controls frequency of wakeups in accel low power mode plus the sensor standby modes
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_PWR_MGMT_2, 0x00)
        # Enables any I2C master interrupt source to generate an interrupt
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_INT_ENABLE, 0x01)
        # enable the FIFO
        self.enable_fifo()
        logger.info("Initialised device")

    def is_accelerometer_enabled(self):
        """
        tests whether acceleration is currently enabled
        :return: true if it is
        """
        return (self.fifo_sensor_mask & self.enable_accelerometer_mask) == self.enable_accelerometer_mask

    def enable_accelerometer(self):
        """
        Specifies the device should write acceleration values to the FIFO, is not applied until enableFIFO is called.
        :return:
        """
        logger.warning("Enabling acceleration sensor")
        self.fifo_sensor_mask |= self.enable_accelerometer_mask
        self._accel_enabled = True
        self._set_sample_size_bytes()

    def disable_accelerometer(self):
        """
        Specifies the device should NOT write acceleration values to the FIFO, is not applied until enableFIFO is
        called.
        :return: 
        """
        logger.warning("Disabling acceleration sensor")
        self.fifo_sensor_mask &= ~self.enable_accelerometer_mask
        self._accel_enabled = False
        self._set_sample_size_bytes()

    def is_gyro_enabled(self):
        """
        tests whether gyro is currently enabled
        :return: true if it is
        """
        return (self.fifo_sensor_mask & self.enableGyroMask) == self.enableGyroMask

    def enable_gyro(self):
        """
        Specifies the device should write gyro values to the FIFO, is not applied until enableFIFO is called.
        :return: 
        """
        logger.warning("Enabling gyro sensor")
        self.fifo_sensor_mask |= self.enableGyroMask
        self._gyro_enabled = True
        self._set_sample_size_bytes()

    def disable_gyro(self):
        """
        Specifies the device should NOT write gyro values to the FIFO, is not applied until enableFIFO is called.
        :return: 
        """
        logger.warning("Disabling gyro sensor")
        self.fifo_sensor_mask &= ~self.enableGyroMask
        self._gyro_enabled = False
        self._set_sample_size_bytes()

    def is_temperature_enabled(self):
        """
        tests whether temperature is currently enabled
        :return: true if it is
        """
        return (self.fifo_sensor_mask & self.enableTemperatureMask) == self.enableTemperatureMask

    def enable_temperature(self):
        """
        Specifies the device should write temperature values to the FIFO, is not applied until enableFIFO is called.
        :return: 
        """
        logger.warning("Enabling temperature sensor")
        self.fifo_sensor_mask |= self.enableTemperatureMask
        self._set_sample_size_bytes()

    def disable_temperature(self):
        """
        Specifies the device should NOT write temperature values to the FIFO, is not applied until enableFIFO is called.
        :return: 
        """
        logger.warning("Disabling temperature sensor")
        self.fifo_sensor_mask &= ~self.enableTemperatureMask
        self._set_sample_size_bytes()

    def set_gyro_sensitivity(self, value):
        """
        Sets the gyro sensitivity to 250, 500, 1000 or 2000 according to the given value (and implicitly disables the
        self
        tests)
        :param value: the target sensitivity.
        """
        try:
            self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_GYRO_CONFIG,
                              {250: 0, 500: 8, 1000: 16, 2000: 24}[value])
            self._gyro_factor = value / 32768.0
            self.gyro_sensitivity = value
            logger.warning(f"Set gyro sensitivity = {value}")
        except KeyError:
            raise ArgumentError(value + " is not a valid sensitivity (250,500,1000,2000)")

    def set_accelerometer_sensitivity(self, value):
        """
        Sets the accelerometer sensitivity to 2, 4, 8 or 16 according to the given value. Throws an ArgumentError if
        the value provided is not valid.
        :param value: the target sensitivity.
        """
        # note that this implicitly disables the self tests on each axis
        # i.e. the full byte is actually 000[accel]000 where the 1st 3 are the accelerometer self tests, the next two
        # values are the actual sensitivity and the last 3 are unused
        # the 2 [accel] bits are translated by the device as follows; 00 = 2g, 01 = 4g, 10 = 8g, 11 = 16g
        # in binary we get 2 = 0, 4 = 1000, 8 = 10000, 16 = 11000
        # so the 1st 3 bits are always 0
        try:
            self.i2c_io.write(self.MPU6050_ADDRESS,
                              self.MPU6050_RA_ACCEL_CONFIG,
                              {2: 0, 4: 8, 8: 16, 16: 24}[value])
            self._acceleration_factor = value / 32768.0
            self.accelerometer_sensitivity = value
            logger.warning(f"Set accelerometer sensitivity = {value}")
        except KeyError:
            raise ArgumentError(value + " is not a valid sensitivity (2,4,8,18)")

    def set_sample_rate(self, target_fs):
        """
        Sets the internal sample rate of the MPU-6050, this requires writing a value to the device to set the sample
        rate as Gyroscope Output Rate / (1 + SMPLRT_DIV) where the gryoscope outputs at 8kHz and the peak sampling rate
         is 1kHz. The target sample rate is therefore capped at 1kHz.
        :param target_fs: the target sample rate.
        :return:
        """
        sample_rate_denominator = int((8000 / min(target_fs, 1000)) - 1)
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_SMPLRT_DIV, sample_rate_denominator)
        self.fs = 8000.0 / (sample_rate_denominator + 1.0)
        logger.warning(f"Set sample rate = {self.fs}")

    def reset_fifo(self):
        """
        Resets the FIFO by first disabling the FIFO then sending a FIFO_RESET and then re-enabling the FIFO.
        :return:
        """
        logger.info("Resetting FIFO")
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_USER_CTRL, 0b00000000)
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_USER_CTRL, 0b00000100)
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_USER_CTRL, 0b01000000)
        self.get_interrupt_status()
        self.__fifo_reads = 0

    def enable_fifo(self):
        """
        Enables the FIFO, resets it and then sets which values should be written to the FIFO.
        :return:
        """
        logger.info("Enabling FIFO")
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_FIFO_EN, 0)
        self.reset_fifo()
        self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_FIFO_EN, self.fifo_sensor_mask)
        logger.info("Enabled FIFO")

    def get_interrupt_status(self):
        """
         reads and clears the current interrupt status. The byte that can be read is
         0b00010000 = FIFO_OFLOW_INT = FIFO has overflowed
         0b00001000 = I2C_MST_INT = I2C master interrupt has fired
         0b00000001 = DATA_RDY_INT = data is available to read
        """
        return self.i2c_io.read(self.MPU6050_ADDRESS, self.MPU6050_RA_INT_STATUS)

    def get_fifo_count(self):
        """
        gets the amount of data available on the FIFO right now.
        :return: the number of bytes available on the FIFO which will be proportional to the number of samples available
        based on the values the device is configured to sample.
        """
        b = self.i2c_io.read_block(self.MPU6050_ADDRESS, self.MPU6050_RA_FIFO_COUNTH, 2)
        count = (b[0] << 8) + b[1]
        if count > 64:
            logger.warning(f"FIFO Count: {count}")
            self.__fifo_reads = 0
        else:
            self.__fifo_reads += 1
            if self.__fifo_reads % 10000 == 0:
                logger.info(f"10k consecutive fifo reads with less than 64 bytes")
        return count

    def get_data_from_fifo(self, bytes_to_read):
        """
        reads the specified number of bytes from the FIFO, should be called after a call to getFifoCount to ensure there
        is new data available (to avoid reading duplicate data).
        :param bytes_to_read: the number of bytes to read.
        :return: the bytes read.
        """
        return self.i2c_io.read_block(self.MPU6050_ADDRESS, self.MPU6050_RA_FIFO_R_W, bytes_to_read)

    def provide_data(self):
        """
        reads a batchSize batch of data from the FIFO while attempting to optimise the number of times we have to read
        from the device itself.
        :return: a list of data where each item is a single sample of data converted into real values and stored as a
        dict.
        """
        samples = []
        fifo_bytes_available = 0
        fifo_was_reset = False
        logger.debug(">> provideData target %d samples", self.samples_per_batch)
        iterations = 0
        # allow 1.5x the expected duration of the batch
        break_time = time() + ((self.samples_per_batch / self.fs) * 1.5)
        overdue = False
        interrupt = 0x00
        while len(samples) < self.samples_per_batch and not overdue:
            iterations += 1
            if iterations > self.samples_per_batch and iterations % 100 == 0:
                if time() > break_time:
                    logger.warning("Breaking measurement after %d iterations, batch overdue", iterations)
                    overdue = True
            if fifo_bytes_available < self.sample_size_bytes or fifo_was_reset:
                interrupt = self.get_interrupt_status()
                fifo_bytes_available = self.get_fifo_count()
                fifo_was_reset = False
            logger.debug("Start sample loop [available: %d , required: %d]", fifo_bytes_available, self.sample_size_bytes)
            if interrupt & 0x10:
                logger.error("FIFO OVERFLOW, RESETTING [available: %d , interrupt: %d]", fifo_bytes_available, interrupt)
                self.sample_idx = -1
                self.reset_fifo()
                fifo_was_reset = True
            elif fifo_bytes_available == 1024:
                logger.error("FIFO FULL, RESETTING [available: %d , interrupt: %d]", fifo_bytes_available, interrupt)
                self.sample_idx = -1
                self.reset_fifo()
                fifo_was_reset = True
            elif interrupt & 0x02 or interrupt & 0x01:
                # wait for at least 1 sample to arrive, should be a VERY short wait
                while fifo_bytes_available < self.sample_size_bytes:
                    logger.debug("Waiting for sample [available: %d , required: %d]", fifo_bytes_available,
                                 self.sample_size_bytes)
                    fifo_bytes_available = self.get_fifo_count()
                logger.debug("Processing data [available: %d , required: %d]", fifo_bytes_available, self.sample_size_bytes)
                fifo_read_bytes = self.sample_size_bytes
                # TODO this chunk of code is a bit messy, tidy it up
                # if we have more than 1 sample available then ensure we read as many as we can at once (albeit within
                # the limits of the max i2c read size of 32 bytes)
                if fifo_bytes_available > self.sample_size_bytes:
                    fifo_read_bytes = min(fifo_bytes_available // self.sample_size_bytes,
                                        self.max_bytes_per_fifo_read) * self.sample_size_bytes
                    logger.debug("Excess bytes to read [available: %d , reading: %d]", fifo_bytes_available,
                                 fifo_read_bytes)
                # but don't read more than we need to fulfil the batch
                samples_to_read = fifo_read_bytes // self.sample_size_bytes
                excess_samples = self.samples_per_batch - len(samples) - samples_to_read
                if excess_samples < 0:
                    samples_to_read += excess_samples
                    fifo_read_bytes = int(samples_to_read * self.sample_size_bytes)
                    logger.debug("Excess samples to read [available: %d , reading: %d]", fifo_bytes_available,
                                 fifo_read_bytes)
                else:
                    logger.debug("Reading [available: %d , reading: %d]", fifo_bytes_available, fifo_read_bytes)
                # read the bytes from the fifo, break it into sample sized chunks and convert to the actual values
                fifo_bytes = self.get_data_from_fifo(fifo_read_bytes)
                samples.extend([self.unpack_sample(fifo_bytes[i:i + self.sample_size_bytes])
                                for i in range(0, len(fifo_bytes), self.sample_size_bytes)])
                # track the count here so we can avoid going back to the FIFO each time
                fifo_bytes_available -= fifo_read_bytes
                logger.debug("End sample loop [available: %d , required: %d]", fifo_bytes_available, self.sample_size_bytes)
        logger.debug("<< provideData %d samples", len(samples))
        return samples

    def unpack_sample(self, raw_data):
        """
        unpacks a single sample of data (where sample length is based on the currently enabled sensors).
        :param raw_data: the data to convert
        :param fifo_bytes_available: the bytes left on the FIFO, allows estimation of the actual sample time.
        :return: a converted data set.
        """
        length = len(raw_data)
        # TODO error if not multiple of 2
        # logger.debug(">> unpacking sample %d length %d", self._sampleIdx, length)
        unpacked = struct.unpack(">" + ('h' * (length // 2)), memoryview(bytearray(raw_data)).tobytes())
        # store the data in an array
        data = [None] * (2
                         + (3 if self.is_accelerometer_enabled() else 0)
                         + (1 if self.is_temperature_enabled() else 0)
                         + (3 if self.is_gyro_enabled() else 0))
        self.sample_idx = self.sample_idx + 1
        data[0] = self.sample_idx
        data[1] = self.time_zero
        sensor_idx = 0
        if self.is_accelerometer_enabled():
            data[sensor_idx + 2] = unpacked[sensor_idx] * self._acceleration_factor
            sensor_idx += 1
            data[sensor_idx + 2] = unpacked[sensor_idx] * self._acceleration_factor
            sensor_idx += 1
            data[sensor_idx + 2] = unpacked[sensor_idx] * self._acceleration_factor
            sensor_idx += 1

        if self.is_temperature_enabled():
            data[sensor_idx + 2] = unpacked[sensor_idx] * self._temperatureGain + self._temperatureOffset
            sensor_idx += 1

        if self.is_gyro_enabled():
            data[sensor_idx + 2] = unpacked[sensor_idx] * self._gyro_factor
            sensor_idx += 1
            data[sensor_idx + 2] = unpacked[sensor_idx] * self._gyro_factor
            sensor_idx += 1
            data[sensor_idx + 2] = unpacked[sensor_idx] * self._gyro_factor
            sensor_idx += 1
        # logger.debug("<< unpacked sample length %d into vals size %d", length, len(output))
        return data

    def perform_self_test(self):
        """
        performs a self calibration against factory settings.
        :return:
        boolean: true if all sensors pass self test
        dictionary: all underlying percentage deviations, +/-14% is a pass
        """
        try:
            logger.info(">> selfTest")
            # enable self test on all axes and set range to +/-250
            self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_GYRO_CONFIG, 0b11100000)
            # enable self test on all axes and set range to +/-8g
            self.i2c_io.write(self.MPU6050_ADDRESS, self.MPU6050_RA_ACCEL_CONFIG, 0b11110000)
            # sleep to let the test run
            sleep(0.5)
            # read the resulting raw data
            raw_data = [self.i2c_io.read(self.MPU6050_ADDRESS, 0x0D),
                        self.i2c_io.read(self.MPU6050_ADDRESS, 0x0E),
                        self.i2c_io.read(self.MPU6050_ADDRESS, 0x0F),
                        self.i2c_io.read(self.MPU6050_ADDRESS, 0x10)]
            # each value is a 5 bit unsigned int that packs in both gyro and acceleration results
            # acceleration is in bits 5-7
            acceleration = {
                'x': (raw_data[0] >> 3) | (raw_data[3] & 0x30) >> 4,
                'y': (raw_data[1] >> 3) | (raw_data[3] & 0x0C) >> 4,
                'z': (raw_data[2] >> 3) | (raw_data[3] & 0x03) >> 4
            }
            # calculate results
            factory_trim_acceleration = {
                'x': (4096.0 * 0.34) * (pow((0.92 / 0.34), ((acceleration['x'] - 1.0) / 30.0))),
                'y': (4096.0 * 0.34) * (pow((0.92 / 0.34), ((acceleration['y'] - 1.0) / 30.0))),
                'z': (4096.0 * 0.34) * (pow((0.92 / 0.34), ((acceleration['z'] - 1.0) / 30.0)))
            }
            # gyro is in bits 0-4
            gyro = {
                'x': raw_data[0] & 0x1F,
                'y': raw_data[1] & 0x1F,
                'z': raw_data[2] & 0x1F
            }
            # calculate results
            factory_trim_gyro = {
                'x': (25.0 * 131.0) * (pow(1.046, (gyro['x'] - 1.0))),
                'y': (-25.0 * 131.0) * (pow(1.046, (gyro['y'] - 1.0))),
                'z': (25.0 * 131.0) * (pow(1.046, (gyro['z'] - 1.0)))
            }
            # percent diffs
            results = {}
            for axis in ['x', 'y', 'z']:
                results['a' + axis] = 100.0 + 100.0 * (acceleration[axis] - factory_trim_acceleration[axis]) / \
                                              factory_trim_acceleration[axis]
                results['g' + axis] = 100.0 + 100.0 * (gyro[axis] - factory_trim_gyro[axis]) / factory_trim_gyro[axis]

            passed = all(abs(v) < 14 for v in results.values())
            if passed:
                logger.info("self test passed")
            else:
                logger.error("SELF TEST FAILURE " + str(results))
            return passed, results
        finally:
            self.set_accelerometer_sensitivity(self.accelerometer_sensitivity)
            self.set_gyro_sensitivity(self.gyro_sensitivity)
            logger.info("<< selfTest")
