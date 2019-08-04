import json
import logging
from enum import Enum

from twisted.internet.protocol import Factory, connectionDone
from twisted.protocols.basic import LineReceiver

from qvibe.handler import DataHandler, ERROR

logger = logging.getLogger(__name__)


class Command(Enum):
    GET = 1
    SET = 2
    STR = 3


class SocketHandler(DataHandler):

    def __init__(self, protocol):
        self.protocol = protocol

    def handle(self, data):
        for datum in data:
            if isinstance(datum, dict):
                self.protocol.sendLine(json.dumps(datum).encode())
            elif isinstance(datum, list):
                self.protocol.sendLine(json.dumps(datum).encode())
            elif datum == ERROR:
                self.protocol.sendLine(ERROR.encode())
            else:
                logger.error(f"Unknown data type {datum.__class__.__name__}")

    def on_init_fail(self, event_time, message):
        pass


class CommandProtocol(LineReceiver):

    def __init__(self, devices):
        self.devices = devices
        self.handlers = [v.data_handler.accept(None) for _, v in devices.items()]

    def rawDataReceived(self, data):
        pass

    def connectionLost(self, reason=connectionDone):
        # TODO allow multiple connections?
        for h in self.handlers:
            h.accept(None)

    def connectionMade(self):
        self.send_all_device_states()
        for h in self.handlers:
            h.accept(SocketHandler(self))

    def send_all_device_states(self):
        self.send_device_state([d.state for d in self.devices.values()])

    def send_device_state(self, device_state):
        import json
        y = json.dumps(device_state)
        self.sendLine(f"{len(y)}|{y}".encode())

    def lineReceived(self, line):
        tokens = line.decode().split('|')
        try:
            cmd = Command[tokens[0]]
            if cmd == Command.GET:
                self.handle_get(tokens)
            elif cmd == Command.SET:
                self.handle_set(tokens)
            elif cmd == Command.STR:
                self.handle_str(tokens)
        except KeyError as e:
            logger.info(f"Unknown command in {line}")
        except Exception as e:
            logger.exception(f"Failed to handle command - {line}")

    def handle_str(self, tokens):
        if len(tokens) == 2:
            device_name = tokens[1]
            if device_name in self.devices:
                import json
                self.sendLine(json.dumps(self.devices[device_name].self_test_results).encode())

    def handle_set(self, tokens):
        import json
        target_state = json.loads(tokens[1])
        if 'name' in target_state and target_state['name'] in self.devices:
            device = self.devices[target_state['name']]
            device.state = target_state
            self.send_device_state(device.state)

    def handle_get(self, tokens):
        if len(tokens) == 1:
            self.send_all_device_states()
        else:
            device_name = tokens[1]
            if device_name in self.devices:
                self.send_device_state(self.devices[device_name].state)


class CommandFactory(Factory):

    def __init__(self, devices):
        self.devices = devices

    def buildProtocol(self, addr):
        return CommandProtocol(self.devices)
