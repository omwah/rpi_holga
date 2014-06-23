#!/usr/bin/env python

import os
import atexit
from datetime import datetime

from wiringpi2 import *
import picamera

OUTPUT_DIR = '/home/pi/pictures'

BUTTON_PIN = 7
CHIRP_PIN = 6

g = GPIO()
camera = picamera.PiCamera()

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

if __name__ == '__main__':
    boot_ack()
    print '** Camera Ready **'
    while True:
        if g.digitalRead(BUTTON_PIN) == GPIO.LOW:
            chirp(5)
            filename = capture_still()
            print('** Snap ** %s' % filename)
            chirp(5); g.delay(100); chirp(10)

            while g.digitalRead(BUTTON_PIN) == GPIO.LOW:
                g.delay(20)
     
