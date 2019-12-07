#!/usr/bin/env python
# -*- coding: utf-8 -*-

# MIT License (MIT)
# Copyright (c) 2016 Richard Hull, 2019 Thomas Schank

"""
Python BME280 Driver
"""

from bme280.reader import reader
import bme280.const as oversampling
import bme280.usmbus

import logging
import random as random
import sys
import time

logger = logging.getLogger(__name__)

# Oversampling modes
oversampling.x1 = 1
oversampling.x2 = 2
oversampling.x4 = 3
oversampling.x8 = 4
oversampling.x16 = 5

DEFAULT_PORT = 0x76


class params(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def load_calibration_params(bus, address=DEFAULT_PORT):
    """
    The BME280 output consists of the ADC output values. However, each sensing
    element behaves differently. Therefore, the actual pressure and temperature
    must be calculated using a set of calibration parameters.

    The calibration parameters are subsequently used to with some compensation
    formula to perform temperature readout in degC, humidity in % and pressure
    in hPA.
    """
    read = reader(bus, address)
    compensation_params = params()

    # Temperature trimming params
    compensation_params.dig_T1 = read.unsigned_short(0x88)
    compensation_params.dig_T2 = read.signed_short(0x8A)
    compensation_params.dig_T3 = read.signed_short(0x8C)

    # Pressure trimming params
    compensation_params.dig_P1 = read.unsigned_short(0x8E)
    compensation_params.dig_P2 = read.signed_short(0x90)
    compensation_params.dig_P3 = read.signed_short(0x92)
    compensation_params.dig_P4 = read.signed_short(0x94)
    compensation_params.dig_P5 = read.signed_short(0x96)
    compensation_params.dig_P6 = read.signed_short(0x98)
    compensation_params.dig_P7 = read.signed_short(0x9A)
    compensation_params.dig_P8 = read.signed_short(0x9C)
    compensation_params.dig_P9 = read.signed_short(0x9E)

    # Humidity trimming params
    compensation_params.dig_H1 = read.unsigned_byte(0xA1)
    compensation_params.dig_H2 = read.signed_short(0xE1)
    compensation_params.dig_H3 = read.signed_byte(0xE3)

    e4 = read.signed_byte(0xE4)
    e5 = read.signed_byte(0xE5)
    e6 = read.signed_byte(0xE6)

    compensation_params.dig_H4 = e4 << 4 | e5 & 0x0F
    compensation_params.dig_H5 = ((e5 >> 4) & 0x0F) | (e6 << 4)
    compensation_params.dig_H6 = read.signed_byte(0xE7)

    return compensation_params


class BME280():

    def __init__(self, bus, address=DEFAULT_PORT, sampling=oversampling.x1):
        if sys.implementation.name == 'cpython':
            self.bus = bus
        elif sys.implementation.name == 'micropython':
            self.bus = bme280.usmbus.SMBusWrapper(bus)
        else:
            raise Exception("OS {} is not supported".format(sys.implementation.name))
        self.address = address
        self.sampling = sampling
        self.delay=self.calc_delay()
        self.last_sample = {}
        self.mode = 1  # forced
        self._comp = load_calibration_params(self.bus, address)
        logger.info("BME280 base initialized")

    def calc_delay(self):
        t_delay = 0.000575 + 0.0023 * (1 << self.sampling)
        h_delay = 0.000575 + 0.0023 * (1 << self.sampling)
        p_delay = 0.001250 + 0.0023 * (1 << self.sampling)
        return t_delay + h_delay + p_delay


    def set_uncompensated_readings(self, block):
        self.raw_pressure = (block[0] << 16 | block[1] << 8 | block[2]) >> 4
        self.raw_temperature = (block[3] << 16 | block[4] << 8 | block[5]) >> 4
        self.raw_humidity = block[6] << 8 | block[7]


    def calc_temp(self):
        t = self.raw_temperature
        v1 = (t / 16384.0 - self._comp.dig_T1 / 1024.0) * self._comp.dig_T2
        v2 = ((t / 131072.0 - self._comp.dig_T1 / 8192.0) ** 2) * self._comp.dig_T3
        self.__tfine= v1 + v2
        self.temperature = self.__tfine / 5120.0

    def calc_humidity(self):
        h = self.raw_humidity
        t = self.raw_temperature

        res = self.__tfine - 76800.0
        res = (h - (self._comp.dig_H4 * 64.0 + self._comp.dig_H5 / 16384.0 * res)) * (self._comp.dig_H2 / 65536.0 * (1.0 + self._comp.dig_H6 / 67108864.0 * res * (1.0 + self._comp.dig_H3 / 67108864.0 * res)))
        res = res * (1.0 - (self._comp.dig_H1 * res / 524288.0))
        self.humidity =  max(0.0, min(res, 100.0))

    def calc_pressure(self):
        p = self.raw_pressure
        t = self.raw_temperature
        v1 = self.__tfine / 2.0 - 64000.0
        v2 = v1 * v1 * self._comp.dig_P6 / 32768.0
        v2 = v2 + v1 * self._comp.dig_P5 * 2.0
        v2 = v2 / 4.0 + self._comp.dig_P4 * 65536.0
        v1 = (self._comp.dig_P3 * v1 * v1 / 524288.0 + self._comp.dig_P2 * v1) / 524288.0
        v1 = (1.0 + v1 / 32768.0) * self._comp.dig_P1

        # Prevent divide by zero
        if v1 == 0:
            self.pressure = 0
            return

        res = 1048576.0 - p
        res = ((res - v2 / 4096.0) * 6250.0) / v1
        v1 = self._comp.dig_P9 * res * res / 2147483648.0
        v2 = res * self._comp.dig_P8 / 32768.0
        res = res + (v1 + v2 + self._comp.dig_P7) / 16.0
        self.pressure = res/100.0


    def set_compensated_readings(self):
        self.id = random.getrandbits(32)
        self.timestamp = time.time()
        self.calc_temp()
        self.calc_humidity()
        self.calc_pressure()
        self.last_sample = {
                "timestamp": round(self.timestamp),
                "temperature": round(self.temperature, 1),
                "humidity": int(round(self.humidity, 0)),
                "pressure": round(self.pressure, 1)}

    def request_sample(self):
        self.bus.write_byte_data(self.address, 0xF2, self.sampling)  # ctrl_hum
        self.bus.write_byte_data(self.address, 0xF4, self.sampling << 5 | self.sampling << 2 | self.mode)  # ctrl

    def read_and_evaluate_sample(self):
        data = self.bus.read_i2c_block_data(self.address, 0xF7, 8)
        self.set_uncompensated_readings(data)
        self.set_compensated_readings()

    def sample(self):
        self.request_sample()
        time.sleep(self.delay)
        self.read_and_evaluate_sample()

    def __str__(self):
        return "{} last sample: {}".format(self.__class__.__name__, self.last_sample)

