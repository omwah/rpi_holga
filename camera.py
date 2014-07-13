#!/usr/bin/env python

import os
import sys
import shutil
import atexit
import signal
import logging
import subprocess
from datetime import datetime
from multiprocessing import Process, Queue

from wiringpi2 import *
from PIL import Image
import picamera

from preview.config import Config
from preview.image import resize_image

RESOLUTION = (2592, 1944)

# Ratio of how much of image can be blank before moving to a seperate
# blank directory
MAX_BLANK_AMOUNT = 0.89

BUTTON_PIN = 7
BEEP_PIN = 6

ROTARY_SWITCH = { 3:1, 2:2, 0:3, 4:4, 5:5 }

LOG_FORMAT = '%(asctime)s -- %(message)s'

class HolgaCamera(object):

    def __init__(self, post_proc_queue):
        self.g = GPIO()
        self.g.pinMode(BEEP_PIN, GPIO.OUTPUT)

        self.rotary_pos = 0

        self.rpi_camera = None

        self.post_proc_queue = post_proc_queue

        atexit.register(self.teardown)
        signal.signal(signal.SIGTERM, self.teardown)
        
    # Make sure beep pin is off even when code is stopped mid beep
    def teardown(self):
        logging.debug('Running teardown')
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
            logging.debug('Initializing RPi Camera')
            self.rpi_camera = picamera.PiCamera()
            self.rpi_camera.resolution = RESOLUTION

    def disable_camera(self):
        if self.rpi_camera:
            logging.debug('Disabling RPi Camera')
            self.rpi_camera.close()
            self.rpi_camera = None

    def capture_still(self):
        if self.rpi_camera:
            filebase = datetime.strftime(datetime.now(), '%Y%m%dT%H%M%S%f.jpg')
            filename = os.path.join(Config.IMAGES_ORIGINAL_DIR, filebase)

            # Beep before and after capture so user has a indication
            # on how long the image is taking to take. This can keep
            # you from shaking or moving the camera prematurely
            logging.debug('Begin capture')
            self.beep(5)
            self.rpi_camera.capture(filename)
            self.beep(5); self.g.delay(100); self.beep(10)

            # Send off the filename to get a thumbnail made
            self.post_proc_queue.put(filename)

            logging.debug('End capture')
            logging.debug('Saved picture to: %s' % filename)
            return filename

    def check_shutter_button(self):
        if self.g.digitalRead(BUTTON_PIN) == GPIO.LOW:
            filename = self.capture_still()

            while self.g.digitalRead(BUTTON_PIN) == GPIO.LOW:
                self.g.delay(20)

    def rotary_action(self, new_pos):
        logging.debug('Rotary pos: %s' % new_pos)

        self.beep(duration=20, repeat=new_pos, delay=200)

        if new_pos >= 2:
            self.init_camera()
        else:
            self.disable_camera()

        if new_pos == 5:
            subprocess.call(['shutdown', '-h', 'now'])

    def check_rotary_switch(self):
        for w_pin, r_pos in ROTARY_SWITCH.items():
            if self.g.digitalRead(w_pin) == GPIO.LOW and r_pos != self.rotary_pos:
                self.rotary_pos = r_pos
                self.rotary_action(r_pos)

def post_processor(post_proc_queue, cam):
    logging.info('Post processor ready')
    while True:
        orig_filename = post_proc_queue.get()

        # Resize image first since that is fast and cheaper to analyze using PIL
        tn_filename = os.path.join(Config.IMAGES_THUMBNAIL_DIR, os.path.basename(orig_filename))
        resize_image(orig_filename, tn_filename, Config.IMAGES_THUMBNAIL_SIZE)

        # Check if image is mostly blank, due to lens cap on
        # if so then move to blank directory and remove thumbnail
        logging.debug("Analyzing if image is blank")

        tn_img = Image.open(tn_filename)
        hist = tn_img.histogram()
        per_blank = hist.count(0)/float(len(hist))

        logging.debug("Image is %.2f%% blank" % (per_blank*100))

        if per_blank > MAX_BLANK_AMOUNT:
            logging.debug("Image is blank, moving to blank directory: %s" % orig_filename)
            cam.beep(duration=5, repeat=5, delay=15)
            shutil.move(orig_filename, Config.IMAGES_BLANK_DIR)
            os.remove(tn_filename)

if __name__ == '__main__':
    if not os.path.exists(Config.IMAGES_ORIGINAL_DIR):
        os.makedirs(Config.IMAGES_ORIGINAL_DIR)

    # Set up logging
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG, stream=sys.stderr)

    # Create a seperate thread to post process images, such as thumbnails
    post_proc_queue = Queue()

    cam = HolgaCamera(post_proc_queue)

    post_processing = Process(target=post_processor, args=(post_proc_queue,cam))
    post_processing.start()

    cam.beep(duration=20, repeat=5, delay=100)
    logging.info('RPi Holga Camera Ready')

    while True:
        cam.check_shutter_button()
        cam.check_rotary_switch()
    
        # Delay briefly so don't use 100% CPU
        delay(200)
