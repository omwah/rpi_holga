import os

PICTURES_BASE_DIR = '/home/pi/pictures'

class Config(object):
    DEBUG = True
    IMAGES_THUMBNAIL_SIZE = (390, 293)
    IMAGES_ORIGINAL_DIR = PICTURES_BASE_DIR
    IMAGES_THUMBNAIL_DIR = os.path.join(PICTURES_BASE_DIR, 'thumbnail')
