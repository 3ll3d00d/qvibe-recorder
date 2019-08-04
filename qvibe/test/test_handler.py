import os
import shutil
import time

from qvibe.handler import DataHandler, AsyncHandler, CSVLogger


class MyHandler(DataHandler):
    def __init__(self):
        self.event_time = None
        self.events = []
        self.message = None

    def on_init_fail(self, event_time, message):
        self.event_time = event_time
        self.message = message

    def handle(self, data):
        self.events.append(data)


def test_async_handles_all_events():
    logger = MyHandler()
    async_handler = AsyncHandler(delegate=logger)
    do_loop(async_handler)
    time.sleep(0.5)
    assert len(logger.events) == 100
    for i in range(0, 100):
        assert logger.events[i] == make_event(i)


def do_loop(handler, use_list_vals=False):
    for i in range(0, 100):
        handler.handle(make_event(i, use_list_vals))
    handler.on_init_fail(time.time(), "endtest")


def make_event(i, use_list_vals=False):
    import collections
    dict = collections.OrderedDict()
    dict["d"] = "d" + str(i)
    dict["b"] = "b" + str(i)
    if use_list_vals:
        return [list(dict.values())]
    else:
        return [dict]


def test_csvWritesEachRowToFile(tmpdir):
    output_dir = setupCsv(tmpdir)
    logger = CSVLogger('owner', output_dir)
    do_loop(logger)
    verifyCsv(tmpdir)


def test_csvWritesEachRowToFileWhenAcceptingValues(tmpdir):
    output_dir = setupCsv(tmpdir)
    logger = CSVLogger('owner', output_dir)
    do_loop(logger, True)
    verifyCsv(tmpdir, True)


def test_csvWritesEachRowToFileWhenAsync(tmpdir):
    output_dir = setupCsv(tmpdir)
    logger = CSVLogger('owner', output_dir)
    async_handler = AsyncHandler(logger)
    do_loop(async_handler)
    time.sleep(0.5)
    verifyCsv(tmpdir)


def setupCsv(tmpdir):
    output_dir = os.path.join(tmpdir, "test")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    return output_dir


def verifyCsv(tmpdir, use_list_vals=False):
    output_file = os.path.join(tmpdir, "test", 'owner', 'data.out')
    assert os.path.exists(output_file)
    with open(output_file) as f:
        lines = f.read().splitlines()

    if use_list_vals is True:
        assert len(lines) == 100
        for i in range(0, 100):
            assert lines[i] == "d" + str(i) + ",b" + str(i)
    else:
        assert len(lines) == 101
        assert lines[0] == "d,b"
        for i in range(0, 100):
            assert lines[i + 1] == "d" + str(i) + ",b" + str(i)
