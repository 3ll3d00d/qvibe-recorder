import faulthandler
import logging
import threading

from twisted.internet.endpoints import TCP4ServerEndpoint

from qvibe.config import Config
from qvibe.handler import AsyncHandler
from qvibe.i2cio import WhiteNoiseProvider, mockIO, smbusIO
from qvibe.interface import CommandFactory
from qvibe.mpu6050 import mpu6050
from twisted.internet import reactor


logger = logging.getLogger(__name__)

# register a thread dumper
faulthandler.enable()
if hasattr(faulthandler, 'register'):
    import signal

    faulthandler.register(signal.SIGUSR2, all_threads=True)


def create_device(device_cfg):
    """
    Creates a measurement device from the input configuration.
    :param: device_cfg: the device cfg.
    :return: the constructed device.
    """
    io_cfg = device_cfg['io']
    device_type = device_cfg['type']
    if device_type == 'mpu6050':
        fs = device_cfg.get('fs')
        name = device_cfg.get('name', 'mpu6050')
        if io_cfg['type'] == 'mock':
            provider = io_cfg.get('provider')
            if provider is not None and provider == 'white noise':
                data_provider = WhiteNoiseProvider()
            else:
                raise ValueError(provider + " is not a supported mock io data provider")
            logger.warning("Loading mock data provider for mpu6050")
            io = mockIO(data_provider=data_provider.provide)
        elif io_cfg['type'] == 'smbus':
            bus_id = io_cfg['busId']
            logger.warning("Loading smbus %d", bus_id)
            io = smbusIO(bus_id)
        else:
            raise ValueError(io_cfg['type'] + " is not a supported io provider")
        logger.warning(f"Loading mpu6050 {name}/{fs}")
        samples_per_batch = int(device_cfg['samplesPerBatch']) if 'samplesPerBatch' in device_cfg else None
        mpu = mpu6050(io, name=name, fs=fs, data_handler=AsyncHandler(), self_test=True,
                      samples_per_batch=samples_per_batch)
        worker = threading.Thread(target=mpu.run, daemon=True)
        worker.start()
        return mpu
    else:
        raise ValueError(device_type + " is not a supported device")


def run(args=None):
    """ The main routine. """
    cfg = Config()
    cfg.configure_logger()
    devices = {device.name: device for device in [create_device(c) for c in cfg.config['accelerometers']]}
    endpoint = TCP4ServerEndpoint(reactor, cfg.port)
    logger.info(f"Listening on port {cfg.port}")
    endpoint.listen(CommandFactory(devices))
    reactor.run()


if __name__ == '__main__':
    run()
