# CS1237: Python class for the CS1237 ADC

This is a very short and simple class. 

## Constructor

### cs1237 = CS1237(clock_pin, data_pin[, gain=1, rate=10, channel=0])

This is the GPIO constructor. data_pin and clock_pin are the pin objects
of the GPIO pins used for the communication. The arguments for gain, rate and channel
are optional and can later be re-configured using the init() method.

## Methods

### cs1237.init(gain=None, rate=None, channel=None)

Configures or re-configures the ADC. All arguments are optional.
Accepted values for **gain** are 1, 2, 64, 128 and for 
**rate** are 10, 40, 640, 1280.
Channel values are:

- 0 : ADC reading
- 1 : Chip retention (sleep?)
- 2 : Temperature reading
- 3 : Internal short of the input

### result = cs1237.read()

Returns the actual reading of the ADC or temperature.


### cs1237.get_config()

Returns the tuple of (gain, rate, channel) as read back from the ADC.


### cs1237.config_status()

Returns True if a new configuration has been properly updated.

### cs1237.calibrate_temperature(temp [, reference_value])

Set the calibration values for the temperature sensor. temp is the actual
°C value. If both the temperature and a reference value are supplied,
it is taken as the calibration tuple of the sensor. If not, the
reference value is read from the sensor. In that case, the device has
first to be configured for temperature reading.  
The reference value can be obtained by configuring the sensor for temperature
reading and calling cs1237.read().

### cs1237.temperature(temp)

Return the actual temperature reading. The reference point has to be
configured before using calibrate_temperature().
The device has first to be configured for temperature reading.

### cs1237.power_down()

Set the load cell to sleep mode.

### cs1237.power_up()

Switch the load cell on again.

### cs1237.is_read()

Tells whether a value can be obtained using cs1237.read()


More methods exists but are used only internally by the CS1237 class.

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

value = cs1237.read()

cs1237.init(gain=2)
value = cs1237.read()

gain, rate, channel = cs1237.get_config()

# Calibrate the temperature reading
cs1237.init(gain=1, rate=10, channel=2)
cs1237.calibrate_temperature(22.1)

# get the temperature
cs1237.init(gain=1, rate=10, channel=2)
temp_celsius = cs1237.temperature()

# Calibrate the temperature reading using a known set point
# which has to be determined only once for a device.

cs1237.calibrate_temperature(20.0, 769000)

```
