import os
import logging

from PIL import Image, ImageOps

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
