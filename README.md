# CS1237: Python class for the CS1237 ADC

This is a very short and simple class. 

## Constructor

### cs1237 = CS1237(clock_pin, data_pin[, gain=CS1237.GAIN_1, rate=CS1237.RATE_40, channel=CS1237.CHANNEL_A])

This is the GPIO constructor. data_pin and clock_pin are the pin objects
of the GPIO pins used for the communication. The arguments for gain, rate and channel
are optional and can later be re-configured using the init() method.

## Methods

### cs1237.init(gain=None, rate=None, channel=None)

Configures or re-configures the ADC. All arguments are optional. The
class constants to be used for gain, rate and channel are shown below.


### result = cs1237.read_value()

Returns the actual reading of the ADC or temperature.


### cs1237.get_config()

Returns the tuple of (gain, rate, channel) as read back from the ADC.


### cs1237.config_status()

Returns True if a new configuration has been properly updated.

### cs1237.power_down()

Set the load cell to sleep mode.

### cs1237.power_up()

Switch the load cell on again.

### cs1237.is_read()

Tells whether a value can be obtained using cs1237.read_value()


More methods exists but are used only internally by the CS1237 class.

## Class constants

    GAIN_1
    GAIN_2
    GAIN_64
    GAIN_128

    RATE_10
    RATE_40
    RATE_640
    RATE_1280

    CHANNEL_A
    CHANNEL_TEMP

## Examples


```
# Connections:
# Pin # | CS1237
# ------|-----------
# 12    | data_pin
# 13    | clock_pin
#

from cs1237 import CS1237
from machine import Pin

data = Pin(12)
clock = Pin(13)

# Create a CS1237 instance with default values for gain, rate and channel
cs1237 = CS1237(clock, data)

value = cs1237.read_value()

cs1237.init(gain=cs1237.GAIN_64)
value = cs1237.read_value()

gain, rate, channel = cs1237.get_config()
```
