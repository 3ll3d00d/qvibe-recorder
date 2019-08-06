import abc
import logging
import time

from qvibe.handler import Discard, ERROR

NAME = 'name'
FS = 'fs'
SAMPLE_IDX = 'idx'
ZERO_TIME = 'zt'
ACCEL_X = 'ac_x'
ACCEL_Y = 'ac_y'
ACCEL_Z = 'ac_z'
GYRO_X = 'gy_x'
GYRO_Y = 'gy_y'
GYRO_Z = 'gy_z'
TEMP = 'temp'

logger = logging.getLogger(__name__)


class Accelerometer:
    """
    A simple base class to represent an accelerometer, exists to enable the system to be tested in the absence of a
    physical device.
    """

    def __init__(self, fs=None, samples_per_batch=None, data_handler=None):
        """
        Initialises the accelerometer to use a default sample rate of 500Hz, a samplesPerBatch that accommodates 1/4s
        worth of data and a dataHandler function that simply logs data to the screen.
        :param: fs: the sample rate
        :param: samplesPerBatch: the number of samples that each provideData block should yield.
        :param: dataHandler: a function that accepts the data produced by initialiseDevice and does something with it.
        """
        if fs is None:
            self.fs = 500
        else:
            self.fs = fs
        if samples_per_batch is None:
            self.samples_per_batch = self.fs / 4
        else:
            self.samples_per_batch = samples_per_batch
        if data_handler is None:
            self.data_handler = Discard()
        else:
            self.data_handler = data_handler
        self.__last_overflow = None

    def run(self):
        while True:
            logger.warning("Running")
            if self.do_init() is True:
                self.record()
            else:
                time.sleep(1)

    def do_init(self):
        try:
            logger.info("Initialising device")
            self.initialise_device()
            logger.info("Initialisation complete")
            return True
        except Exception as e:
            logger.exception("Initialisation failed")
            self.data_handler.on_init_fail(time.time(), str(e))
            return False

    def record(self):
        try:
            while True:
                self.data_handler.handle(self.provide_data())
        except Exception as e:
            logger.exception('Unexpected exception during record loop')
            self.data_handler.handle(ERROR)

    @abc.abstractmethod
    def provide_data(self):
        """
        reads the underlying device to provide a batch of raw data.
        :return: a list of data where each item is a single sample of data converted into real values and stored as a
        dict.
        """
        pass

    @abc.abstractmethod
    def initialise_device(self):
        """
        initialises the underlying device
        """
        pass
