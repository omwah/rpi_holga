import os
import sys
import dircache
import logging
from collections import namedtuple
from optparse import OptionParser

from flask import Flask, url_for, render_template, send_file
from PIL import Image, ImageOps

def configure_app(app):
    app.config.from_object('config.Config')

def make_image_dirs(app):
    for img_dir in ('IMAGES_ORIGINAL_DIR', 'IMAGES_THUMBNAIL_DIR'):
        if not os.path.exists(app.config[img_dir]):
            os.makedirs(app.config[img_dir])

app = Flask(__name__)

configure_app(app)
make_image_dirs(app)

class CameraPicture(object):
    def __init__(self, filename):
        self.filename = filename
        self.basename = os.path.basename(filename)
        self.title = os.path.basename(filename)

    @property
    def original(self):
        return url_for('original', filename=self.basename)

    @property
    def thumbnail(self):
        TnInfo = namedtuple('TnInfo', ['src', 'width', 'height'])
        src = url_for('thumbnail', filename=self.basename)
        width = app.config['IMAGES_THUMBNAIL_SIZE'][0]
        height = app.config['IMAGES_THUMBNAIL_SIZE'][1]
        return TnInfo(src, width, height)

def image_filenames():
    img_fns = sorted(dircache.listdir(app.config['IMAGES_ORIGINAL_DIR']), reverse=True)
    return img_fns

@app.route('/')
def index():
    pictures = []
    for filename in image_filenames():
        img_filename = os.path.join(app.config['IMAGES_ORIGINAL_DIR'], filename)
        if os.path.isfile(img_filename):
            pictures.append(CameraPicture(img_filename))
    return render_template('pictures.html', pictures=pictures)

@app.route('/original/<filename>')
def original(filename):
    orig_filename = os.path.join(app.config['IMAGES_ORIGINAL_DIR'], filename)
    return send_file(orig_filename)

def resize_image(orig_filename, new_filename, size, fit=False):
    if os.path.realpath(orig_filename) == os.path.realpath(new_filename):
        raise IOException('Original and resized filename can not be the same: %s' % orig_filename)

    if not os.path.exists(new_filename):
        logging.debug("Generating (%s) image for %s" % (size, orig_filename))
        im = Image.open(orig_filename)
        if fit:
            thumb = ImageOps.fit(im, size, Image.ANTIALIAS)
            thumb.save(new_filename)
        else:
            im.thumbnail(size, Image.ANTIALIAS)
            im.save(new_filename)
        return True

    return False

@app.route('/thumbnail/<filename>')
def thumbnail(filename):
    orig_filename = os.path.join(app.config['IMAGES_ORIGINAL_DIR'], filename)
    img_filename = os.path.join(app.config['IMAGES_THUMBNAIL_DIR'], filename)
    resize_image(orig_filename, img_filename, app.config['IMAGES_THUMBNAIL_SIZE'], fit=True)
    return send_file(img_filename)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--host", dest="host", action="store", type="str",
                      default=None, help="The network host the app will use")
    parser.add_option("--port", dest="port", action="store", type="int",
                      default=None, help="The network port the app will use")
    (options, args) = parser.parse_args()

    # Set up logging
    FORMAT = "%(name)s -- %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG, stream=sys.stderr)

    app.run(debug=app.config['DEBUG'], host=options.host, port=options.port)
