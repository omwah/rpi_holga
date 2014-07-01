#!/usr/bin/env python

import os
import atexit
from datetime import datetime
import subprocess

from wiringpi2 import *
import picamera

OUTPUT_DIR = '/home/pi/pictures'
RESOLUTION = (2592, 1944)

BUTTON_PIN = 7
CHIRP_PIN = 6

ROTARY_SWITCH = { 3:1, 2:2, 0:3, 4:4, 5:5 }

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

g = GPIO()
camera = picamera.PiCamera()
camera.resolution = RESOLUTION

g.pinMode(CHIRP_PIN, GPIO.OUTPUT)

def chirp(duration=20):
    g.digitalWrite(CHIRP_PIN, GPIO.HIGH)
    g.delay(duration)
    g.digitalWrite(CHIRP_PIN, GPIO.LOW)

# Make sure chirp pin is off even when code is stopped mid chirp
def teardown():
    g.digitalWrite(CHIRP_PIN, GPIO.LOW)
atexit.register(teardown)

def boot_ack():
    for _ in range(5):
        chirp(20)
        g.delay(100)

def capture_still():
    filename = datetime.strftime(datetime.now(), '%Y%m%dT%H%M%S%f.jpg')
    camera.capture(os.path.join(OUTPUT_DIR, filename))
    return filename

def rotary_action(new_pos):
    print "Rotary pos:", new_pos

    if new_pos == 5:
        for _ in range(7):
            chirp(20)
            g.delay(200)
        subprocess.call(["shutdown", "-h", "now"])

if __name__ == '__main__':
    boot_ack()
    print '** Camera Ready **'

    rotary_pos = 0
    while True:
        if g.digitalRead(BUTTON_PIN) == GPIO.LOW:
            chirp(5)
            filename = capture_still()
            print('** Snap ** %s' % filename)
            chirp(5); g.delay(100); chirp(10)

            while g.digitalRead(BUTTON_PIN) == GPIO.LOW:
                g.delay(20)

        for w_pin, r_pos in ROTARY_SWITCH.items():
            if g.digitalRead(w_pin) == GPIO.LOW and r_pos != rotary_pos:
                rotary_pos = r_pos
                rotary_action(r_pos)
     
        # Delay briefly so don't use 100% CPU
        delay(200)
