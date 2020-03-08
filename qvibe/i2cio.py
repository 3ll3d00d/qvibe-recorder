import abc
from queue import Queue

from qvibe.mpu6050 import mpu6050


class i2cIO(object):
    """
    A thin wrapper on the smbus for reading and writing data. Exists to allow unit testing without a real device
    connected.
    """

    def __init__(self):
        pass

    """
    Writes data to the device.
    :param: i2c_address: the address to write to.
    :param: register: the location to write to.
    :param: val: the value to write.
    """

    @abc.abstractmethod
    def write(self, i2c_address, register, val):
        pass

    """
    Reads data from the device.
    :param: i2c_address: the address to read from.
    :param: register: the register to read from.
    :return: the data read.
    """

    @abc.abstractmethod
    def read(self, i2c_address, register):
        pass

    """
    Reads a block of data from the device.
    :param: i2c_address: the address to read from.
    :param: register: the register to read from.
    :param: length: no of bytes to read.
    :return: the data read.
    """

    @abc.abstractmethod
    def read_block(self, i2c_address, register, length):
        pass


class mockIO(i2cIO):
    def __init__(self, data_provider=None):
        super().__init__()
        self.values_written = []
        self.data_provider = data_provider
        self.vals_to_read = Queue()

    def write(self, i2c_address, register, val):
        self.values_written.append([i2c_address, register, val])

    def read_block(self, i2c_address, register, length):
        if self.data_provider is not None:
            ret = self.data_provider(register, length)
            if ret is not None:
                return ret
        return self.vals_to_read.get_nowait()

    def read(self, i2c_address, register):
        if self.data_provider is not None:
            ret = self.data_provider(register)
            if ret is not None:
                return ret
        return self.vals_to_read.get_nowait()


class MockIoDataProvider:

    def __init__(self, samples):
        self.idx = 0
        self.samples = samples

    def provide(self, register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01
        elif register is mpu6050.MPU6050_RA_FIFO_COUNTH:
            # always 36 bytes
            return [0b00000000, 0b00100100]
        elif register is mpu6050.MPU6050_RA_FIFO_R_W:
            to_read = length // 6
            bytes = bytearray()
            for i in range(0, to_read):
                self.add_value(bytes, 'x')
                self.add_value(bytes, 'y')
                self.add_value(bytes, 'z')
                self.idx += 1
            from time import sleep
            sleep(0.002 * to_read)
            return bytes
        else:
            if length is None:
                return 0b00000000
            else:
                return [x.to_bytes(1, 'big') for x in range(length)]

    def add_value(self, bytes, key):
        samples = self.samples[key]
        sample_val = samples[self.idx % len(samples)]
        val = self.convert_value(sample_val)
        try:
            b = bytearray(val.to_bytes(2, 'big'))
        except OverflowError:
            print("Value too big - " + str(val) + " - replacing with 0")
            val = 0
            b = bytearray(val.to_bytes(2, 'big'))
        bytes.extend(b)

    def convert_value(self, val):
        i = int((val * 32768))
        return i if i >= 0 else 65536 + i


class ModulatedNoiseProvider(MockIoDataProvider):

    def __init__(self):
        import random
        super().__init__({
            'x': [random.gauss(0, 0.25) for _ in range(0, 1000)],
            'y': [random.gauss(0, 0.25) for _ in range(0, 1000)],
            'z': [random.gauss(0, 0.25) for _ in range(0, 1000)]
        })


class WhiteNoiseProvider(MockIoDataProvider):

    def __init__(self):
        import random
        super().__init__({
            'x': [random.gauss(0, 0.25) for _ in range(0, 1000)],
            'y': [random.gauss(0, 0.25) for _ in range(0, 1000)],
            'z': [random.gauss(0, 0.25) for _ in range(0, 1000)]
        })


class WavProvider(MockIoDataProvider):
    '''
    Reads data created from a wav file as per
     f.write(struct.pack('d'*len(data), *data))
    '''
    def __init__(self, file):
        import struct
        import os
        sz = os.stat(file).st_size
        if sz % 8 != 0:
            raise ValueError(f"File size is {sz}, can't be a dbl file")
        with open(file, mode='rb') as f:
            data = list(struct.unpack('d' * int(sz / 8), f.read(sz)))
        if data is not None:
            super().__init__({
                'x': data,
                'y': data,
                'z': data
            })


class smbusIO(i2cIO):
    """
    an implementation of i2c_io which talks over the smbus.
    """

    def __init__(self, bus_id=1):
        super().__init__()
        from smbus2 import SMBus
        self.bus = SMBus(bus=bus_id)

    def write(self, i2c_address, register, val):
        """
        Delegates to smbus.write_byte_data
        """
        return self.bus.write_byte_data(i2c_address, register, val)

    def read(self, i2c_address, register):
        """
        Delegates to smbus.read_byte_data
        """
        return self.bus.read_byte_data(i2c_address, register)

    def read_block(self, i2c_address, register, length):
        """
        Delegates to smbus.read_i2c_block_data
        """
        return self.bus.read_i2c_block_data(i2c_address, register, length)
