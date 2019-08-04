import abc
import csv
import logging
import os
import threading
from queue import Queue, Empty

logger = logging.getLogger(__name__)

ERROR = 'ERROR'


class DataHandler:
    """
    A simple interface to define the expected behaviour of something that handles data.
    """

    @abc.abstractmethod
    def handle(self, data):
        """
        A callback for handling some raw data.
        :param data a list of dicts containing the sample data
        :return:
        """
        pass

    @abc.abstractmethod
    def on_init_fail(self, event_time, message):
        """
        Callback for handling initialisation failures.
        :param event_time: the time of the event.
        :param message: the message.
        """
        pass


class Discard(DataHandler):
    """
    a data handler that simply throws the data away
    """

    def handle(self, data):
        pass

    def on_init_fail(self, event_time, message):
        pass


class CSVLogger(DataHandler):
    """
    A handler which logs the received data to CSV into target/name/data.out
    """

    def __init__(self, name, target):
        self.name = name
        self.target = target
        self._csv = None
        self._csvfile = None
        self._first = True
        target_dir = os.path.join(self.target, self.name)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, 'data.out')
        if os.path.exists(target_path):
            mode = 'w'
        else:
            mode = 'x'
        self.__csvfile = open(target_path, mode=mode, newline='')
        self.__csv = csv.writer(self.__csvfile)
        self.__first = True

    def handle(self, data):
        """
        Writes each sample to a csv file.
        :param data: the samples.
        :return:
        """
        for datum in data:
            if isinstance(datum, dict):
                if self.__first:
                    self.__csv.writerow(datum.keys())
                    self.__first = False
                self.__csv.writerow(datum.values())
            elif isinstance(datum, list):
                self.__csv.writerow(datum)
            self.__csvfile.flush()

    def on_init_fail(self, event_time, message):
        # TODO write an error message
        pass


class AsyncHandler(DataHandler):
    """
    A handler which hands the data off to another thread.
    """

    def __init__(self, delegate=None):
        self.name = "Async"
        self.delegate = delegate
        self.queue = Queue()
        self.worker = None
        self.worker = threading.Thread(target=self.async_handle, daemon=True)
        self.worker.start()

    def accept(self, delegate):
        self.delegate = delegate
        return self

    def handle(self, data):
        if self.delegate is not None:
            self.queue.put(data, block=False)

    def on_init_fail(self, event_time, message):
        if self.delegate is not None:
            self.delegate.on_init_fail(event_time, message)

    def async_handle(self):
        while True:
            try:
                event = self.queue.get(timeout=1)
                if event is not None:
                    if self.delegate is not None:
                        self.delegate.handle(event)
                    self.queue.task_done()
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"async queue has {self.queue.qsize()} items")
            except Empty:
                pass
