""" Provides an SMBus class for use on micropython """

# MIT License
# Copyright (c) 2017 Geoff Lee, 2019 Tom Schank
#
# adopted from https://github.com/gkluoe/micropython-smbus
# this variant does not extend but really wrap machine.I2C
# which is less intrusive in some cirumstances


class SMBusWrapper():
    """ Provides an 'SMBus' module which supports some of the py-smbus
        i2c methods
	"""

    def __init__(self, i2c):
        self.i2c = i2c

    def read_byte_data(self, addr, register):
        """ Read a single byte from register of device at addr
            Returns a single byte """
        return self.i2c.readfrom_mem(addr, register, 1)[0]

    def read_i2c_block_data(self, addr, register, length):
        """ Read a block of length from register of device at addr
            Returns a bytes object filled with whatever was read """
        return self.i2c.readfrom_mem(addr, register, length)

    def write_byte_data(self, addr, register, data):
        """ Write a single byte from buffer `data` to register of device at addr
            Returns None """
        # writeto_mem() expects something it can treat as a buffer
        if isinstance(data, int):
            data = bytes([data])
        return self.i2c.writeto_mem(addr, register, data)

    def write_i2c_block_data(self, addr, register, data):
        """ Write multiple bytes of data to register of device at addr
            Returns None """
        # writeto_mem() expects something it can treat as a buffer
        if isinstance(data, int):
            data = bytes([data])
        return self.i2c.writeto_mem(addr, register, data)

    # The follwing haven't been implemented, but could be.
    def read_byte(self, *args, **kwargs):
        """ Not yet implemented """
        raise RuntimeError("Not yet implemented")

    def write_byte(self, *args, **kwargs):
        """ Not yet implemented """
        raise RuntimeError("Not yet implemented")

    def read_word_data(self, addr, register):
        d = self.i2c.readfrom_mem(addr, register, 2)
        return (d[1] << 8 | d[0]) & 0xffff

    def write_word_data(self, *args, **kwargs):
        """ Not yet implemented """
        raise RuntimeError("Not yet implemented")

