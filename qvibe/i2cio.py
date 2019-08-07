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
    @abc.abstractmethod
    def provide(self, register):
        pass


class WhiteNoiseProvider(MockIoDataProvider):
    """
    A mock io provider which yields white noise.
    """

    def __init__(self):
        import random
        self.samples = {
            'x': [random.gauss(0, 0.25) for _ in range(0, 1000)],
            'y': [random.gauss(0, 0.25) for _ in range(0, 1000)],
            'z': [random.gauss(0, 0.25) for _ in range(0, 1000)]
        }
        self.idx = 0

    def provide(self, register, length=None):
        if register is mpu6050.MPU6050_RA_INT_STATUS:
            return 0x01
        elif register is mpu6050.MPU6050_RA_FIFO_COUNTH:
            return [0b0000, 0b1100]
        elif register is mpu6050.MPU6050_RA_FIFO_R_W:
            bytes = bytearray()
            self.add_value(bytes, 'x')
            self.add_value(bytes, 'y')
            self.add_value(bytes, 'z')
            self.idx += 1
            self.add_value(bytes, 'x')
            self.add_value(bytes, 'y')
            self.add_value(bytes, 'z')
            from time import sleep
            sleep(0.002)
            return bytes
        else:
            if length is None:
                return 0b00000000
            else:
                return [x.to_bytes(1, 'big') for x in range(length)]

    def add_value(self, bytes, key):
        val = abs(int((self.samples[key][self.idx % 1000] * 32768)))
        try:
            b = bytearray(val.to_bytes(2, 'big'))
        except OverflowError:
            print("Value too big - " + str(val) + " - replacing with 0")
            val = 0
            b = bytearray(val.to_bytes(2, 'big'))
        bytes.extend(b)


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
