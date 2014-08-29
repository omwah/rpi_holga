#!/usr/bin/env python

import os
import sys
import shutil
import atexit
import signal
import logging
import subprocess
from datetime import datetime
from fractions import Fraction
from multiprocessing import Process, Queue

from wiringpi2 import *
from PIL import Image
import picamera

from preview.config import Config
from preview.image import resize_image

# Ratio of how much of image can be blank before moving to a seperate
# blank directory
MAX_BLANK_AMOUNT = 0.89

BUTTON_PIN = 7
BEEP_PIN = 6

# Maps a wiringPi GPIO pin to a rotary switch position
ROTARY_SWITCH = { 4:1, 2:2, 3:3, 0:4, 1:5 }

# Changes camera settings depending on rotary switch position
DEFAULT_SETTINGS = { 'framerate': Fraction(30, 1), 
                     'shutter_speed': 0, 
                     'exposure_mode': 'auto', 
                     'ISO': 0,
                     'resolution': (2592, 1944),
                    } # defaults
ROTARY_SETTINGS = { 3: { 'framerate': Fraction(1, 6), # low light
                         'shutter_speed': 6000000, 
                         'exposure_mode': 'off', 
                         'ISO': 800, },
                  }

SCREEN_FORMAT = '%(asctime)s -- %(message)s'
LOG_FORMAT = '%(asctime)s -- %(message)s'
LOG_FILENAME = '/home/pi/logs/rpi_camera.log'

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

    def set_camera_attributes(self, attrs):
        if not self.rpi_camera:
            logging.error('Camera is not initialized, can not set attributes')
            return

        logging.debug('Setting camera attributes:')
        for attr_name, attr_val in attrs.items():
            if not hasattr(self.rpi_camera, attr_name):
                logging.error('Camera has no attribute: %s' % attr_name)
                continue
            logging.debug('\t%s = %s' % (attr_name, attr_val))
            setattr(self.rpi_camera, attr_name, attr_val)

    def apply_settings(self, rotary_pos=None):
        # First apply defaults
        cam_settings = DEFAULT_SETTINGS.copy()
        if rotary_pos and ROTARY_SETTINGS.has_key(rotary_pos):
            cam_settings.update(ROTARY_SETTINGS[rotary_pos])
        self.set_camera_attributes(cam_settings)

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
            self.apply_settings(new_pos)
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

def init_logging(verbose=False, log_file=None):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
       
    # Start up console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt=SCREEN_FORMAT))

    logger.addHandler(console)
    
    # Log to a file if the option is supplied
    if log_file:
        log_dir = os.path.dirname(log_file)
        if len(log_dir) > 0 and not os.path.exists(log_dir):
            os.makedirs(os.path.dirname(log_file))

        logger = logging.getLogger()
        fileout = logging.FileHandler(log_file, "w")
        fileout.setLevel(logging.DEBUG)
        fileout.setFormatter(logging.Formatter(fmt=LOG_FORMAT))
        logger.addHandler(fileout)

if __name__ == '__main__':
    if not os.path.exists(Config.IMAGES_ORIGINAL_DIR):
        os.makedirs(Config.IMAGES_ORIGINAL_DIR)

    # Set up logging
    init_logging(verbose=True, log_file=LOG_FILENAME)

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
