from random import randint

from qvibe.i2cio import mockIO
from qvibe.mpu6050 import mpu6050


def test_default_state():
    def provider(register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01

    mpu = mpu6050(mockIO(data_provider=provider), self_test=False)
    assert mpu.is_accelerometer_enabled()
    assert not mpu.is_temperature_enabled()
    assert not mpu.is_gyro_enabled()
    assert mpu.fs == 500
    assert mpu.samples_per_batch == 125


def test_canToggleAccelerometer():
    mpu = mpu6050(mockIO(), self_test=False)
    assert mpu.is_accelerometer_enabled()
    mpu.disable_accelerometer()
    assert not mpu.is_accelerometer_enabled()
    mpu.enable_accelerometer()
    assert mpu.is_accelerometer_enabled()
    mpu.disable_accelerometer()
    assert not mpu.is_accelerometer_enabled()


def test_canToggleGyro():
    mpu = mpu6050(mockIO(), self_test=False)
    mpu.enable_gyro()
    assert mpu.is_gyro_enabled()
    mpu.disable_gyro()
    assert not mpu.is_gyro_enabled()
    mpu.enable_gyro()
    assert mpu.is_gyro_enabled()
    mpu.disable_gyro()
    assert not mpu.is_gyro_enabled()


def test_canToggleTemperature():
    mpu = mpu6050(mockIO(), self_test=False)
    mpu.enable_temperature()
    assert mpu.is_temperature_enabled()
    mpu.disable_temperature()
    assert not mpu.is_temperature_enabled()
    mpu.enable_temperature()
    assert mpu.is_temperature_enabled()
    mpu.disable_temperature()
    assert not mpu.is_temperature_enabled()


def test_whenSensorsAreToggled_fifoPacketSizeIsCorrect():
    mpu = mpu6050(mockIO(), self_test=False)
    # -gyro-temperature+acceleration
    assert mpu.get_packet_size() == 6
    assert mpu.fifo_sensor_mask == 0b00001000
    mpu.enable_gyro()
    # +gyro-temperature+acceleration
    assert mpu.get_packet_size() == 12
    assert mpu.fifo_sensor_mask == 0b01111000
    mpu.enable_temperature()
    # +gyro+temperature+acceleration
    assert mpu.get_packet_size() == 14
    assert mpu.fifo_sensor_mask == 0b11111000
    mpu.disable_accelerometer()
    # +gyro+temperature-acceleration
    assert mpu.get_packet_size() == 8
    assert mpu.fifo_sensor_mask == 0b11110000
    mpu.disable_gyro()
    # -gyro+temperature-acceleration
    assert mpu.get_packet_size() == 2
    assert mpu.fifo_sensor_mask == 0b10000000
    mpu.disable_temperature()
    # -gyro-temperature-acceleration
    assert mpu.get_packet_size() == 0
    assert mpu.fifo_sensor_mask == 0b00000000
    mpu.enable_gyro()
    # +gyro-temperature-acceleration
    assert mpu.get_packet_size() == 6
    assert mpu.fifo_sensor_mask == 0b01110000
    mpu.disable_gyro()
    mpu.enable_accelerometer()
    mpu.enable_temperature()
    # -gyro+temperature+acceleration
    assert mpu.get_packet_size() == 8
    assert mpu.fifo_sensor_mask == 0b10001000


def test_sampleRateMaxesAt1000():
    io = mockIO()
    mpu = mpu6050(io, self_test=False)
    io.values_written.clear()
    mpu.set_sample_rate(2000)
    assert 1000 == mpu.fs
    # check the correct SMPLRT_DIV is written to the device
    assert len(io.values_written) == 1
    assert io.values_written[0][2] == 7


def test_sampleRateCanBeUpdatedToLessThan1000():
    io = mockIO()
    mpu = mpu6050(io, self_test=False)
    io.values_written.clear()
    mpu.set_sample_rate(200)
    assert 200 == mpu.fs
    # check the correct SMPLRT_DIV is written to the device
    assert len(io.values_written) == 1
    assert io.values_written[0][2] == 39


def test_getFifoCount():
    values = (
        ((0b00000000, 0b00000000), 0),
        ((0b00000001, 0b00000000), 256),
        ((0b00000000, 0b00000001), 1),
        ((0b00000001, 0b00000001), 257),
        ((0b10000000, 0b10000000), 32896),
        ((0b11111111, 0b10000000), 65408),
    )
    io = mockIO()
    mpu = mpu6050(io, self_test=False)
    for testcase in values:
        io.vals_to_read.put(testcase[0])
        assert mpu.get_fifo_count() == testcase[1]


def test_readSingleBatchWithSixBytesAvailableOnEachRead():
    # provide a constant stream of 6 byte samples
    fifoCounter = 0
    fifoReader = 0
    fifoValues = [0b0000, 0b0001, 0b0010, 0b0011, 0b0100, 0b0101]

    def provider(register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01
        elif register is mpu6050.MPU6050_RA_FIFO_COUNTH:
            nonlocal fifoCounter
            fifoCounter += 1
            return [0b0000, 0b0110]
        elif register is mpu6050.MPU6050_RA_FIFO_R_W:
            nonlocal fifoReader
            fifoReader += 1
            assert length is not None
            assert 6 == length
            return fifoValues

    io = mockIO(data_provider=provider)
    mpu = mpu6050(io, self_test=False)
    output = mpu.provide_data()
    assert output is not None
    assert len(output) == 125
    assert all(len(i) == len(output[0]) for i in output)
    # check all actual values are identical (as a short cut for these are the same values as returned by the fifo)
    assert all(x[1:] == output[0][1:] for x in output)
    assert fifoCounter == 125
    assert fifoReader == 125


def test_readSingleBatchInOneTripToFifo():
    # provide a single 6*125 = 750 byte fifo
    fifoCounter = 0
    fifoReader = 0

    def provider(register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01
        elif register is mpu6050.MPU6050_RA_FIFO_COUNTH:
            nonlocal fifoCounter
            fifoCounter += 1
            return [0b0010, 0b11101110]
        elif register is mpu6050.MPU6050_RA_FIFO_R_W:
            nonlocal fifoReader
            fifoReader += 1
            assert length is not None
            assert 30 == length
            return [0b0000, 0b0001, 0b0010, 0b0011, 0b0100, 0b0101] * 5

    io = mockIO(data_provider=provider)
    mpu = mpu6050(io, self_test=False)
    output = mpu.provide_data()
    assert output is not None
    assert len(output) == 125
    assert all(len(i) == len(output[0]) for i in output)
    # check all actual values are identical (as a short cut for these are the same values as returned by the fifo)
    assert all(x[1:] == output[0][1:] for x in output)
    assert fifoCounter == 1
    assert fifoReader == 25


def test_readSingleBatchWhenLastSizeHasSamplesRemaining():
    fifoCounter = 0
    fifoReader = 0

    def provider(register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01
        elif register is mpu6050.MPU6050_RA_FIFO_COUNTH:
            nonlocal fifoCounter
            fifoCounter += 1
            return [0b00, 0b00001100]
        elif register is mpu6050.MPU6050_RA_FIFO_R_W:
            nonlocal fifoReader
            fifoReader += 1
            assert length is not None
            assert length == 6 or length == 12
            return [0b0000, 0b0001, 0b0010, 0b0011, 0b0100, 0b0101] * (length // 6)

    io = mockIO(data_provider=provider)
    mpu = mpu6050(io, self_test=False)
    output = mpu.provide_data()
    assert output is not None
    assert len(output) == 125
    assert all(len(i) == len(output[0]) for i in output)
    # check all actual values are identical (as a short cut for these are the same values as returned by the fifo)
    assert all(x[1:] == output[0][1:] for x in output)
    assert fifoCounter == 63
    assert fifoReader == 63


def test_readSingleBatchWithFourteenBytesAvailableOnEachReadWhenAllSensorsAreAvailable():
    fifoCounter = 0
    fifoReader = 0

    def provider(register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01
        elif register is mpu6050.MPU6050_RA_FIFO_COUNTH:
            nonlocal fifoCounter
            fifoCounter += 1
            return [0b00, 0b00001110]
        elif register is mpu6050.MPU6050_RA_FIFO_R_W:
            nonlocal fifoReader
            fifoReader += 1
            assert length is not None
            assert length == 14
            return [0b0000, 0b0001, 0b0010, 0b0011, 0b0100, 0b0101, 0b0111,
                    0b1000, 0b1001, 0b1010, 0b1011, 0b1100, 0b1101, 0b1110]

    io = mockIO(data_provider=provider)
    mpu = mpu6050(io, self_test=False)
    mpu.enable_gyro()
    mpu.enable_temperature()
    output = mpu.provide_data()
    assert output is not None
    assert len(output) == 125
    assert all(len(i) == len(output[0]) for i in output)
    # check all actual values are identical (as a short cut for these are the same values as returned by the fifo)
    assert all(x[1:] == output[0][1:] for x in output)
    assert fifoCounter == 125
    assert fifoReader == 125


def test_readSingleBatchWithVaryingFifoSizes():
    fifoCounter = 0
    fifoReader = 0

    def provider(register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01
        elif register is mpu6050.MPU6050_RA_FIFO_COUNTH:
            nonlocal fifoCounter
            fifoCounter += 1
            to_bytes = (randint(1, 50) * 6).to_bytes(2, 'big')
            return to_bytes
        elif register is mpu6050.MPU6050_RA_FIFO_R_W:
            nonlocal fifoReader
            fifoReader += 1
            assert length is not None
            assert length in [6, 12, 18, 24, 30]
            return [0b0000, 0b0001, 0b0010, 0b0011, 0b0100, 0b0101] * (length // 6)

    io = mockIO(data_provider=provider)
    mpu = mpu6050(io, self_test=False)
    output = mpu.provide_data()
    assert output is not None
    assert len(output) == 125
    assert all(len(i) == len(output[0]) for i in output)
    # check all actual values are identical (as a short cut for these are the same values as returned by the fifo)
    assert all(x[1:] == output[0][1:] for x in output)
    # fifo size is randomly generated so can't verify the number of times we read it
