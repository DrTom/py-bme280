import bme280.BME280
import logging
import math as math
import random as random
import time as time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio as asyncio

logger = logging.getLogger(__name__)

class BME280as(bme280.BME280.BME280):

    INTERVAL_SECS_DEFAULT = 60

    def __init__(self,
            bus,
            address=bme280.BME280.DEFAULT_PORT,
            sampling=bme280.BME280.oversampling.x16,
            intervall_secs = INTERVAL_SECS_DEFAULT
            ):
        super().__init__(bus, address=address, sampling=sampling)
        self.intervall_secs = intervall_secs
        self.update_listeners = {}
        self.loop = asyncio.get_event_loop()
        self.loop_id = None
        self.re_start_async_loop()
        logger.info("BME280as initialized")

    def add_update_listener(self, k, listener):
        logger.info("add_update_listener {}".format(k))
        self.update_listeners[k]=listener

    def invoke_listeners(self):
        for k, listener in self.update_listeners.items():
            try:
                listener(self.last_sample)
            except Exception as e:
                logger.warning("Error invoking update_listener {}".format(k))

    async def sample_async_loop(self, loop_id):
        try:
            if self.loop_id == loop_id:
                self.request_sample()
                await asyncio.sleep(self.delay)
            if self.loop_id == loop_id:
                self.read_and_evaluate_sample()
                logger.debug("BME280 new sample: {}".format(self))
                self.invoke_listeners()
        except Exception as e:
            self.readout= { "error": str(e)}
            logger.error(str(e))
        s = 0
        while s < self.intervall_secs and loop_id == self.loop_id:
            s += 1
            await asyncio.sleep(1)
        if self.loop_id == loop_id:
            self.loop.create_task(self.sample_async_loop(loop_id))

    def re_start_async_loop(self):
        loop_id = random.getrandbits(32)
        self.loop_id = loop_id
        self.loop.create_task(self.sample_async_loop(loop_id))
        logger.info(" (re)started async loop loop_id: {:d}".format(loop_id))

