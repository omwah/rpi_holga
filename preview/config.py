import os

PICTURES_BASE_DIR = '/home/mcduffie/Temp/pictures_test'

class Config(object):
    DEBUG = True
    IMAGES_THUMBNAIL_SIZE = (144, 108)
    IMAGES_ORIGINAL_DIR = PICTURES_BASE_DIR
    IMAGES_THUMBNAIL_DIR = os.path.join(PICTURES_BASE_DIR, 'thumbnail')
