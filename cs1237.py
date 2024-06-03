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

    GAIN_1 = 0
    GAIN_2 = 1
    GAIN_64 = 2
    GAIN_128 = 3

    RATE_10 = 0
    RATE_40 = 1
    RATE_640 = 2
    RATE_1280 = 3

    CHANNEL_A = 0
    CHANNEL_TEMP = 2

    def __init__(self, clock, data, gain=GAIN_1, rate=RATE_40, channel=CHANNEL_A, delay_us=1):
        self.clock = clock
        self.data = data
        self.delay_us = delay_us
        self.clock.init(mode=Pin.OUT)
        self.clock(0)
        self.init(gain, rate, channel)

    def __write_bit(self, value):
        self.clock(1)
        time.sleep_us(self.delay_us)
        self.data(value)
        self.clock(0)
        time.sleep_us(self.delay_us)

    def __read_bit(self):
        self.clock(1)
        time.sleep_us(self.delay_us)
        self.clock(0)
        time.sleep_us(self.delay_us)
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
            self.__write_bit((cmd & 0x40) != 0)
            cmd <<= 1
        # write gap bit 37
        self.__write_bit(1)

    def __write_config(self, config):
        self.__write_cmd(_CMD_WRITE)
        # write the configuration byte
        for j in range(8):
            self.__write_bit((config & 0x80) != 0)
            config <<= 1
        # wait one clock cycle
        self.data.init(mode=Pin.IN)
        self.__read_bit()

    def __read_config(self):
        self.__write_cmd(_CMD_READ)
        self.data.init(mode=Pin.IN)
        config = 0
        # read the configuration byte
        for j in range(8):
            config = (config << 1) | self.__read_bit()
        # wait one clock cycle
        self.__read_bit()
        return config

    def __data_ready_cb(self, pin):
        self.__flag_ready = True
        pin.irq(handler=None)

    def read_value(self):
        self.data.init(mode=Pin.IN)
        # set up the trigger for the conversion done signal.
        self.__flag_ready = False
        self.data.irq(trigger=Pin.IRQ_FALLING, handler=self.__data_ready_cb)
        # wait for the device being ready
        for _ in range(200):
            if self.__flag_ready == True:
                break
            time.sleep_ms(1)
        else:
            self.data.irq(handler=None)
            raise OSError("Sensor does not respond")
        # shift in data, and gain & channel info
        result = 0
        for j in range(24):
            result = (result << 1) | self.__read_bit()
        # check sign
        if result > 0x7fffff:
            result -= 0x1000000

        return result

    def set_config(self):
        self.read_value()  ## dummy read value
        self.__write_config(self.rate << 4 | self.gain << 2 | self.channel)

    def get_config(self):
        self.read_value()  ## dummy read value
        config = self.__read_config()
        return (config >> 2 & 0x03, config >> 4 & 0x03, config & 0x03)

    def config_status(self):
        self.read_value()  ## dummy read value
        return self.__write_status() >> 1

    def init(self, gain=None, rate=None, channel=None):
        if gain is not None:
            if gain not in (self.GAIN_1, self.GAIN_2, self.GAIN_64, self.GAIN_128):
                raise ValueError("Invalid Gain")
            self.gain = gain
        if rate is not None:
            if rate not in (self.RATE_10, self.RATE_40, self.RATE_640, self.RATE_1280):
                raise ValueError("Invalid rate")
            self.rate = rate
        if channel is not None:
            if channel not in (self.CHANNEL_A, self.CHANNEL_TEMP):
                raise ValueError("Invalid channel")
            self.channel = channel
        self.set_config()

    def is_ready(self):
        return self.data() == 0

    def power_down(self):
        self.clock(0)
        self.clock(1)

    def power_up(self):
        self.clock(0)
