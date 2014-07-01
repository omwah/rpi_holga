import os

PICTURES_BASE_DIR = '/home/pi/pictures'

class Config(object):
    DEBUG = True
    IMAGES_PREVIEW_SIZE = (648, 486)
    IMAGES_THUMBNAIL_SIZE = (144, 108)
    IMAGES_ORIGINAL_DIR = PICTURES_BASE_DIR
    IMAGES_PREVIEW_DIR = os.path.join(PICTURES_BASE_DIR, 'preview')
    IMAGES_THUMBNAIL_DIR = os.path.join(PICTURES_BASE_DIR, 'thumbnail')
