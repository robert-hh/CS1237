# MIT License

# Copyright (c) 2024 Robert Hammelrath

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from machine import Pin
import time

_CMD_READ = const(0x56)
_CMD_WRITE = const(0x65)


class CS1237:
    _gain = {1: 0, 2: 1, 64: 2, 128: 3}

    _rate = {10: 0, 40: 1, 640: 2, 1280: 3}

    def __init__(self, clock, data, gain=64, rate=10, channel=0):
        self.clock = clock
        self.data = data
        self.data.init(mode=Pin.IN)
        self.clock.init(mode=Pin.OUT)
        self.clock(0)
        # pre-set some values for temperature calibration.
        self.ref_value = 769000
        self.ref_temp = 20
        # determine the number of attempts to find the trigger pulse
        start = time.ticks_us()
        for _ in range(3):
            temp = data()
        spent = time.ticks_diff(time.ticks_us(), start)
        self.__wait_loop = 1_500_000 // spent

        self.init(gain, rate, channel)

    def __repr__(self):
        return "CS1237(gain={}, rate={}, channel={})".format(*self.get_config())

    def __call__(self):
        return self.read()

    def __write_bit(self, value):
        self.clock(1)
        self.data(1 if value != 0 else 0)
        self.clock(0)

    def __read_bit(self):
        # duplicate the clock high call to extend the positive pulse
        self.clock(1)
        self.clock(1)
        self.clock(0)
        return self.data()

    def __write_status(self):
        # get the config write status bits
        write_status = (self.__read_bit() << 1) | self.__read_bit()
        self.__read_bit()
        return write_status

    def __write_cmd(self, cmd):
        # apply clock bits 25..27
        self.__write_status()
        # clock bits 28 and 29, telling that a command follows
        self.__read_bit()
        self.__read_bit()
        # write the command word
        self.data.init(mode=Pin.OUT)
        for j in range(7):
            self.__write_bit(cmd & 0x40)
            cmd <<= 1
        # write gap bit 37
        self.__write_bit(1)

    def __write_config(self, config):
        value = self.read()  # read value
        self.__write_cmd(_CMD_WRITE)
        # write the configuration byte
        for j in range(8):
            self.__write_bit(config & 0x80)
            config <<= 1
        # wait one clock cycle
        self.data.init(mode=Pin.IN)
        self.__read_bit()
        time.sleep_ms(100)
        return value

    def __read_config(self):
        value = self.read()  # read value
        self.__write_cmd(_CMD_READ)
        self.data.init(mode=Pin.IN)
        config = 0
        # read the configuration byte
        for j in range(8):
            config = (config << 1) | self.__read_bit()
        # wait one clock cycle
        self.__read_bit()
        return config, value

    # For best performace do not use __read_bit() here and use
    # local copies of the clock and data pin objects.
    def read(self):
        data = self.data
        clock = self.clock
        # wait for the trigger pulse
        for _ in range(self.__wait_loop):
            if data():
                break
        else:
            raise OSError("No trigger pulse found")
        for _ in range(5000):
            if not data():
                break
            time.sleep_us(100)
        else:
            raise OSError("Sensor does not respond")
        result = 0
        for j in range(24):
            # duplicate the clock high call to extend the positive pulse
            clock(1)
            clock(1)
            clock(0)
            # shift in data
            result = (result << 1) | data()
        # check the sign.
        if result > 0x7FFFFF:
            result -= 0x1000000

        return result

    def get_config(self):
        config, _ = self.__read_config()
        return (
            {value: key for key, value in self._gain.items()}[config >> 2 & 0x03],
            {value: key for key, value in self._rate.items()}[config >> 4 & 0x03],
            config & 0x03,
        )

    def config_status(self):
        self.read()  ## dummy read value
        return self.__write_status() >> 1

    def init(self, gain=None, rate=None, channel=None):
        if gain is not None:
            if gain not in self._gain.keys():
                raise ValueError("Invalid Gain")
            self.gain = self._gain[gain]
        if rate is not None:
            if rate not in self._rate.keys():
                raise ValueError("Invalid rate")
            self.rate = self._rate[rate]
        if channel is not None:
            if not 0 <= channel <= 3:
                raise ValueError("Invalid channel")
            self.channel = channel
        self.__do_sample = False
        self.__write_config(self.rate << 4 | self.gain << 2 | self.channel)

    def calibrate_temperature(self, temp, ref_value=None):
        self.ref_temp = temp
        if ref_value is None:
            config, self.ref_value = self.__read_config()
            if config != 0x02:
                # Set gain=1, rate=10, channel=2 (temperature)
                self.__write_config(0x02)
                # Read the value and restore the previous configuration
                self.ref_value = self.__write_config(config)
        else:
            self.ref_value = ref_value

    def temperature(self):
        config, value = self.__read_config()
        if config != 0x02:
            # set gain=1, rate=10, channel=2 (temperature)
            self.__write_config(0x02)
            # Read the value and restore the previous configuration
            value = self.__write_config(config)
        return value / self.ref_value * (273.15 + self.ref_temp) - 273.15

    def power_down(self):
        self.clock(0)
        self.clock(1)

    def power_up(self):
        self.clock(0)
