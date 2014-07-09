#!/usr/bin/env python

import os
import atexit
import signal
import subprocess
from datetime import datetime

from wiringpi2 import *
import picamera

OUTPUT_DIR = '/home/pi/pictures'
RESOLUTION = (2592, 1944)

BUTTON_PIN = 7
BEEP_PIN = 6

ROTARY_SWITCH = { 3:1, 2:2, 0:3, 4:4, 5:5 }

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
        self.g.digitalWrite(BEEP_PIN, GPIO.LOW)

    def beep(self, duration=20):
        self.g.digitalWrite(BEEP_PIN, GPIO.HIGH)
        self.g.delay(duration)
        self.g.digitalWrite(BEEP_PIN, GPIO.LOW)

    def boot_ack(self):
        for _ in range(5):
            self.beep(20)
            self.g.delay(100)

    def capture_still(self):
        with picamera.PiCamera() as camera:
            camera.resolution = RESOLUTION
            filename = datetime.strftime(datetime.now(), '%Y%m%dT%H%M%S%f.jpg')
            camera.capture(os.path.join(OUTPUT_DIR, filename))
        return filename

    def check_shutter_button(self):
        if self.g.digitalRead(BUTTON_PIN) == GPIO.LOW:
            self.beep(5)
            filename = self.capture_still()
            print('** Snap ** %s' % filename)
            self.beep(5); self.g.delay(100); self.beep(10)

            while self.g.digitalRead(BUTTON_PIN) == GPIO.LOW:
                self.g.delay(20)

    def rotary_action(self, new_pos):
        print "Rotary pos:", new_pos

        if new_pos == 5:
            for _ in range(7):
                self.beep(20)
                self.g.delay(200)
            subprocess.call(["shutdown", "-h", "now"])

    def check_rotary_switch(self):
        for w_pin, r_pos in ROTARY_SWITCH.items():
            if self.g.digitalRead(w_pin) == GPIO.LOW and r_pos != self.rotary_pos:
                self.rotary_pos = r_pos
                self.rotary_action(r_pos)

if __name__ == '__main__':
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    cam = HolgaCamera()

    cam.boot_ack()
    print '** Camera Ready **'

    while True:
        cam.check_shutter_button()
        cam.check_rotary_switch()
    
        # Delay briefly so don't use 100% CPU
        delay(200)
