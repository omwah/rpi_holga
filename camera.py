#!/usr/bin/env python

import os
import sys
import atexit
import signal
import logging
import subprocess
from datetime import datetime

from wiringpi2 import *
import picamera

from preview.config import Config

RESOLUTION = (2592, 1944)

BUTTON_PIN = 7
BEEP_PIN = 6

ROTARY_SWITCH = { 3:1, 2:2, 0:3, 4:4, 5:5 }

LOG_FORMAT = "%(asctime)s -- %(message)s"

class HolgaCamera(object):

    def __init__(self):
        self.g = GPIO()
        self.g.pinMode(BEEP_PIN, GPIO.OUTPUT)

        self.rotary_pos = 0

        self.rpi_camera = None

        atexit.register(self.teardown)
        signal.signal(signal.SIGTERM, self.teardown)
        
    # Make sure beep pin is off even when code is stopped mid beep
    def teardown(self):
        logging.debug("Running teardown")
        self.disable_camera()
        self.g.digitalWrite(BEEP_PIN, GPIO.LOW)

    def beep(self, duration=20, repeat=1, delay=100):
        for _ in range(repeat):
            self.g.digitalWrite(BEEP_PIN, GPIO.HIGH)
            self.g.delay(duration)
            self.g.digitalWrite(BEEP_PIN, GPIO.LOW)
            if repeat > 1:
                self.g.delay(delay)

    def init_camera(self):
        if not self.rpi_camera:
            logging.debug("Initializing RPi Camera")
            self.rpi_camera = picamera.PiCamera()
            self.rpi_camera.resolution = RESOLUTION

    def disable_camera(self):
        if self.rpi_camera:
            logging.debug("Disabling RPi Camera")
            self.rpi_camera.close()
            self.rpi_camera = None

    def capture_still(self):
        if self.rpi_camera:
            filebase = datetime.strftime(datetime.now(), '%Y%m%dT%H%M%S%f.jpg')
            filename = os.path.join(Config.PICTURES_BASE_DIR, filebase)
            logging.debug("Begin capture")
            self.beep(5)
            self.rpi_camera.capture(filename)
            self.beep(5); self.g.delay(100); self.beep(10)
            logging.debug("End capture")
            logging.debug("Saving picture to: %s" % filename)
            return filename

    def check_shutter_button(self):
        if self.g.digitalRead(BUTTON_PIN) == GPIO.LOW:
            filename = self.capture_still()

            while self.g.digitalRead(BUTTON_PIN) == GPIO.LOW:
                self.g.delay(20)

    def rotary_action(self, new_pos):
        logging.debug("Rotary pos: %s" % new_pos)

        self.beep(duration=20, repeat=new_pos, delay=200)

        if new_pos >= 2:
            self.init_camera()
        else:
            self.disable_camera()

        if new_pos == 5:
            subprocess.call(["shutdown", "-h", "now"])

    def check_rotary_switch(self):
        for w_pin, r_pos in ROTARY_SWITCH.items():
            if self.g.digitalRead(w_pin) == GPIO.LOW and r_pos != self.rotary_pos:
                self.rotary_pos = r_pos
                self.rotary_action(r_pos)

if __name__ == '__main__':
    if not os.path.exists(Config.PICTURES_BASE_DIR):
        os.makedirs(Config.PICTURES_BASE_DIR)

    # Set up logging
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG, stream=sys.stderr)

    cam = HolgaCamera()

    cam.beep(duration=20, repeat=5, delay=100)
    logging.info('** Camera Ready **')

    while True:
        cam.check_shutter_button()
        cam.check_rotary_switch()
    
        # Delay briefly so don't use 100% CPU
        delay(200)
