import time
import logging 

import pygatt  # type: ignore

from .constants import CHAR_TX, CHAR_FEEDBACK, PyHatchBabyRestSound

class PyHatchBabyRest(object):
    """ A synchronous interface to a Hatch Baby Rest device using pygatt. """

    def __init__(self):
        """
        Instantiate the interface. Note that either a bluetooth address or a
        name must be specified in order to connect. Address is preferable
        because it will directly connect rather than doing a scan.

        :param addr: A specific address to connect to.
        :param name: A specific name to connect to.
        """

        self.adapter = pygatt.GATTToolBackend()
        self.adapter.start()

    def connect(self, name: str = None, addr: str = None):
        if addr is None and name is None:
            raise ValueError("Either addr or name must be set.")

        if name:
            logging.info("Caution: connecting by name is slow. Use the address for faster connections.")
            logging.info(f"scanning for device with name: {name}")
            devices = self.scan()

            for device in devices:
                if device["name"] == name:
                    logging.info(f'found device with name "{name}" at address {device["address"]}')
                    addr = device["address"]
                    break
            else:
                raise RuntimeError(f"Can't find device with name: {name}.")

        logging.info(f"Connecting to device address: {addr}")
        self.device = self.adapter.connect(
            addr, address_type=pygatt.BLEAddressType.random
        )

        self._refresh_data()

    def _send_command(self, command: str):
        """ Send a command to the device.

        :param command: The command to send.
        """
        self.device.char_write(CHAR_TX, bytearray(command, "utf-8"))
        time.sleep(0.25)
        self._refresh_data()

    def _refresh_data(self) -> None:
        """ Request updated data from the device and set the local attributes. """
        response = [hex(x) for x in self.device.char_read(CHAR_FEEDBACK)]

        # Make sure the data is where we think it is
        assert response[5] == "0x43"  # color
        assert response[10] == "0x53"  # audio
        assert response[13] == "0x50"  # power

        red, green, blue, brightness = [int(x, 16) for x in response[6:10]]

        sound = PyHatchBabyRestSound(int(response[11], 16))

        volume = int(response[12], 16)

        power = not bool(int("11000000", 2) & int(response[14], 16))

        self.color = (red, green, blue)
        self.brightness = brightness
        self.sound = sound
        self.volume = volume
        self.power = power

    def disconnect(self):
        return self.device.disconnect()

    def power_on(self):
        command = "SI{:02x}".format(1)
        self._send_command(command)

    def power_off(self):
        command = "SI{:02x}".format(0)
        self._send_command(command)

    def set_sound(self, sound):
        command = "SN{:02x}".format(sound)
        self._send_command(command)

    def set_volume(self, volume):
        command = "SV{:02x}".format(volume)
        self._send_command(command)

    def set_color(self, red: int, green: int, blue: int):
        self._refresh_data()

        command = "SC{:02x}{:02x}{:02x}{:02x}".format(red, green, blue, self.brightness)
        self._send_command(command)

    def set_brightness(self, brightness: int):
        self._refresh_data()

        command = "SC{:02x}{:02x}{:02x}{:02x}".format(
            self.color[0], self.color[1], self.color[2], brightness
        )
        self._send_command(command)

    def scan(self, with_cache=False):
        """Scan for hatch devices."""
        logging.info("Scanning for local bluetooth devices.")
        return self.adapter.scan()

    @property
    def connected(self):
        return self.device._connected
