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
import rp2

_CMD_READ = const(0x56)
_CMD_WRITE = const(0x65)


class CS1237:
    _gain = {1: 0, 2: 1, 64: 2, 128: 3}
    _rate = {10: 0, 40: 1, 640: 2, 1280: 3}

    def __init__(self, clock, data, gain=64, rate=10, channel=0, pio=0):
        self.clock = clock
        self.data = data
        self.timeout = 1000
        self.cs1237_sm_finished = False
        self.cs1237_sm = rp2.StateMachine(pio * 4, self.cs1237_sm_pio,
            freq=3_000_000, in_base=data, out_base=data, set_base=data, sideset_base=clock)
        self.cs1237_sm.irq(handler=self.__irq_sm_finished, trigger=1)
        self.init(gain, rate, channel)
        # pre-set some values for temperature calibration.
        self.ref_value = 769000
        self.ref_temp = 20

    def __repr__(self):
        return "{}(gain={}, rate={}, channel={})".format(self.__qualname__, *self.get_config())

    def __call__(self):
        return self.read()

    @staticmethod
    @rp2.asm_pio(
        in_shiftdir=rp2.PIO.SHIFT_LEFT,
        out_shiftdir=rp2.PIO.SHIFT_LEFT,
        autopull=False,
        autopush=False,
        out_init=rp2.PIO.OUT_LOW,
        set_init=rp2.PIO.OUT_HIGH,
        sideset_init=rp2.PIO.OUT_LOW
    )
    def cs1237_sm_pio():
        set(pindirs, 0)       .side(0)      # set to input
        pull()                .side(0)      # get the mode
                                            # 0: read data and write status
                                            # 1: Write the configuration
                                            # 2: Read the configuration
        mov(y, osr)           .side(0)      # save it to y
# Wait for a high level = start of the DRDY pulse
        wait(1, pin, 0)
# Wait for a low level = DRDY signal
        wait(0, pin, 0)
# Get the data
        mov(isr, null)        .side(0)      # Preset with 0
        set (x, 27)           .side(1)[1]   # 24 bit data + 4 status, 27 to be set
        label("read_data")                  # because of postdecrement
        nop()                 .side(0)      # need one low clock before reading
        in_(pins, 1)          .side(0)      # shift in one bit
        jmp(x_dec, "read_data").side(1)[1]  # and go for another bit, which
                                            # sets the trailing 29th pulse as well
                                            # which is not shifted into the data
# Done with data + status
        push(noblock)         .side(0)      # publish the result, which is
                                            # 24 bit data || 2 bit status || 2 gap bits
        jmp(y_dec, "do_config").side(0)     # If mode is not zero, config
        jmp("end")            .side(0)
# now send command + config
        label("do_config")
        pull()                .side(0)      # get the command byte into OSR
                                            # properly formatted:
        set(pindirs, 1)       .side(0)      # set to output
        jmp(y_dec, "read_config")
        set (x, 16)           .side(0)[1]   # 7 pulses command + 1 gap pulse +
                                            # 8 pulses config + 1 trailing pulse
                                            # data left aligned for MSB first
        label("cmd_write_config")
        out(pins, 1)          .side(1)[1]   # shift out one bit.
        jmp(x_dec, "cmd_write_config").side(0)[1]    # and go for another bit
        jmp("end")            .side(0)

        label("read_config")
        set (x, 7)            .side(0)[1]   # 7 pulses command + 1 gap pulse
                                            # data left aligned for MSB first
        label("cmd_read_config")
        out(pins, 1)          .side(1)[1]   # shift out one bit.
        jmp(x_dec, "cmd_read_config").side(0)[1]    # and go for another bit

        set(pindirs, 0)       .side(0)      # set to input
        mov(isr, null)        .side(0)      # Preset with 0
        set (x, 7)            .side(1)[1]   # 8 bit data
        label("read_config_data")           # because of postdecrement
        nop()                 .side(0)      # need one low clock before reading
        in_(pins, 1)          .side(0)      # shift in one bit
        jmp(x_dec, "read_config_data").side(1)[1]     # and go for another bit
                                            # implicit 46th pulse here
        push(noblock)         .side(0)      # publish the result or error code

        label("end")
        set(pindirs, 0)       .side(0)      # set to input (could be dropped)
        irq(rel(0))           .side(0)      # finished!

    def __irq_sm_finished(self, sm):
        self.cs1237_sm_finished = True

    def __wait_for_completion(self):
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < self.timeout:
            if self.cs1237_sm_finished:
                return
        else:
            # clear the rx FIFO
            while self.cs1237_sm.rx_fifo() > 0:
                self.cs1237_sm.get()
            raise OSError("sensor timeout")

    def __read_data_status(self):
        self.cs1237_sm_finished = False
        self.cs1237_sm.restart()
        self.cs1237_sm.put(0)  # mode: read data + write status
        self.cs1237_sm.active(1)
        self.__wait_for_completion()
        result = self.cs1237_sm.get()
        self.cs1237_sm.active(0)
        return result

    def __write_status(self):
        # get the config write status bits
        return (self.__read_data_status() >> 2) & 0x03

    def __write_config(self, config):
        self.cs1237_sm_finished = False
        self.cs1237_sm.restart()
        self.cs1237_sm.put(1)  # mode: write the configuration
        self.cs1237_sm.put(_CMD_WRITE << 25 | config << 16)  # cmd + config
        self.cs1237_sm.active(1)
        self.__wait_for_completion()
        value = self.cs1237_sm.get(None, 4)
        self.cs1237_sm.active(0)
        # Check the sign.
        if value > 0x7FFFFF:
            value -= 0x1000000
        return value

    def __read_config(self):
        self.cs1237_sm_finished = False
        self.cs1237_sm.restart()
        self.cs1237_sm.put(2)  # mode: read the configuration
        self.cs1237_sm.put(_CMD_READ << 25)  # set the command word
        self.cs1237_sm.active(1)
        self.__wait_for_completion()
        value = self.cs1237_sm.get(None, 4)
        config = self.cs1237_sm.get()
        self.cs1237_sm.active(0)
        # Check the sign.
        if value > 0x7FFFFF:
            value -= 0x1000000
        return config, value

    def read(self):
        # Get the data.
        result = self.__read_data_status() >> 4
        # Check the sign.
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
        config = self.rate << 4 | self.gain << 2 | self.channel
        self.__write_config(config)

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

class CS1238(CS1237):
    pass

