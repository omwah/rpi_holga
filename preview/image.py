import os
import logging

from PIL import Image, ImageOps

def resize_image(orig_img, new_filename, size, fit=False, filter=Image.BICUBIC):
    if Image.isImageType(orig_img):
        orig_filename = orig_img.filename
    else:
        orig_filename = orig_img

    if os.path.realpath(orig_filename) == os.path.realpath(new_filename):
        raise IOException('Original and resized filename can not be the same: %s' % orig_filename)

    if not os.path.exists(new_filename):
        logging.debug("Generating %s image for %s" % (size, orig_filename))
        if not Image.isImageType(orig_img):
            orig_img = Image.open(orig_filename)

        if fit:
            thumb = ImageOps.fit(orig_img, size, filter)
            thumb.save(new_filename)
        else:
            orig_img.thumbnail(size, filter)
            orig_img.save(new_filename)

        logging.debug("Resizing complete")
        return True

    return False
