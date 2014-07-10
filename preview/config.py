import os

class Config(object):
    DEBUG = True
    IMAGES_THUMBNAIL_SIZE = (272,205)
    PICTURES_BASE_DIR = '/home/pi/pictures'
    IMAGES_ORIGINAL_DIR = PICTURES_BASE_DIR
    IMAGES_THUMBNAIL_DIR = os.path.join(PICTURES_BASE_DIR, 'thumbnail')
    IMAGES_BLANK_DIR = os.path.join(PICTURES_BASE_DIR, 'blank')
