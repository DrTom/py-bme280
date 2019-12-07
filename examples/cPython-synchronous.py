### i2c #######################################################################
### this uses a usb->i2c hardare interface
### see https://www.fischl.de/i2c-mp-usb/

from i2c_mp_usb import I2C_MP_USB as SMBus
bus = SMBus()

### logging ###################################################################
# not required but useful
import logging
logging.getLogger('').addHandler(logging.StreamHandler())
logging.getLogger('').setLevel(logging.DEBUG)

### main ######################################################################
from bme280.BME280 import BME280
bme280s = BME280(bus)
bme280s.sample()
print(bme280s)
