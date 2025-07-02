# CS1237: MicroPython classes for the CS1237 and CS1238 ADC

This is a short and simple class for the CS1237 and CS1238 ADC. It supports reading
the ADC value, reading the temperature and configuring the various device
modes. In the following document, the CS1237 or cs1237 is used for both CS1237 and CS1238, unless
otherwise stated.

Tested with MicroPython ports for RP2040, STM32, SAMD, i.MX RT (e.g. Teensy),
ESP32, ESP8266, NRF52840 and W600. Approximate times for reading an ADC value:

- RP2040 at 125 MHz: 450 µs  
- RP2040 at 125 MHz using PIO: 50 µs  
- PYBD SF6 at 192 MHz: 250 µs  
- Teensy 4.1 at 600 MHz: 100 µs  
- SAMD51 at 120 MHz: 450 µs   
- SAMD21 at 48 MHz: 1.2 ms   
- ESP32 at 160 MHz: 900 µs  
- ESP8266 at 80 MHz: 1.2 ms  
- NRF52840: 800µs.  
- Renesas RA6M2 at 120 MHz: 600µs
- W600 at 80 MHz: 900 µs  

The nrf port has the problem that the device cannot be configured when using the IRQ based driver.
NRF52840 based devices have worked in the test
using the polling driver. Otherwise the CS1237 operates at it's default
mode, which is gain=128, rate=10, channel=0.
pin.irq() seems not to work at the Renesas port, at least not with the tested EV-RA6M2 board.
It can be configured, but refuses to work. The polling driver works.


## Constructor

### cs1237 = CS1237(clock_pin, data_pin[, gain=1, rate=10, channel=0, pio=0])
### cs1238 = CS1238(clock_pin, data_pin[, gain=1, rate=10, channel=0, pio=0])
### cs1237 = CS1237P(clock_pin, data_pin[, gain=1, rate=10, channel=0])
### cs1238 = CS1238P(clock_pin, data_pin[, gain=1, rate=10, channel=0])

This is the GPIO constructor. data_pin and clock_pin are the pin objects
of the GPIO pins used for the communication. The arguments for gain, rate and channel
are optional and can later be re-configured using the config() method.
The argument for pio is only available at the RP2 PIO variant. Suitable values
are 0 and 1. The CS1237 statemachine has a size of 32 words, so it fills a single PIO.
The classes with the "P" suffix use polling to detect the conversion ready pulse.
Otherwise a IRQ is used.

## Methods

### cs1237.config(gain=None, rate=None, channel=None)

Configures or re-configures the ADC. All arguments are optional.
Accepted values for **gain** are 1, 2, 64, 128 and for
**rate** are 10, 40, 640, 1280.
Channel values are:

- 0 : ADC channel 0
- 1 : CS1238: ADC channel 1; CS1237: Chip standby
- 2 : Temperature
- 3 : Internal short of the input

At data rates of 640 and 1280 reading with a slow MCU may return wrong
values, and configuring the device may fail. Then only a power cycle
will reset the device. Since the current consumption of the CS1237 is
low, it can be supplied by a GPIO output, making power cycling easy.  

According to the test, Teensy 4.x, RP2350 and PYBD SF6 work fine at a rate
of 1280. The ESP32, RP2040, SAMD51 and Renesas RA6M2 work fine
at a rate at 640 and can still be configured back. The PIO version of the RP2
driver works fine at all rates.  
ESP8266, nrf52, SAMD21 and W600 can be configured once for a rate
of 640, but cannot reset back to a lower rate and do not support
temperature reading when set to the 640 rate.


### result = cs1237.read()
### result = cs1237()

Returns the actual reading of the ADC or temperature.


### cs1237.get_config()

Returns the tuple of (gain, rate, channel) as read back from the ADC.


### cs1237.config_status()

Returns True if a new configuration has been properly updated.


### cs1237.calibrate_temperature(temp [, reference_value])

Set the calibration values for the temperature sensor. temp is the actual
°C value. If both the temperature and a reference value are supplied,
it is taken as the calibration tuple of the sensor. If not, the
reference value is read from the sensor.
The reference value can be obtained by configuring the sensor for temperature
reading and calling cs1237.read().

### cs1237.temperature()

Return the actual temperature reading. The reference point has to be
configured before using calibrate_temperature().

### cs1237.power_down()

Set the CS1237 device to sleep mode. Not supported by the cs1237 PIO variant.

### cs1237.power_up()

Switch the CS1237 on again. Not supported by the cs1237 PIO variant.


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

# get ADC readings
value = cs1237.read()
# Alternative for reading the value
value = cs1237()

# change the gain
cs1237.config(gain=2)
value = cs1237.read()

# return the ADC settings
gain, rate, channel = cs1237.get_config()

# Alternative for showing the properties
print(cs1237)

# Calibrate the temperature reading
cs1237.calibrate_temperature(22.1)

# get the temperature
temp_celsius = cs1237.temperature()

# Calibrate the temperature reading using a known set point
# which has to be determined only once for a device.
cs1237.calibrate_temperature(20.0, 769000)

```

## Files

- **cs1237.py** CS1237 driver using Interrupts.
- **cs1237_pio.py** CS1237 driver using the PIO state machine. Available for RP2040 and RP2350.
- **cs1237_poll.py** CS1237 driver use polling to detect the sync pulse. The
driver may fail on slow devices like ESP8266, SAMD21 or W600. Replaced by
the classes CS1237P and CS1238P of cs1237.py.
- **README.md**  Documentation file.
- **package.json** Helper file for the mip installer.
- **LICENSE** Separate License file.

