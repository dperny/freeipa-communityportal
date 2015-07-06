""" Module for handling captchas in the community portal. """
from captcha.image import ImageCaptcha
import string
import random
import base64
import hmac

LENGTH = 4
# TODO: this is not a secure key
KEY = 'lol you should probably change this'

class CaptchaHelper(object):
    """Class for making a captcha for the client to display."""
    image_generator = ImageCaptcha()

    def __init__(self):
        """create a new captcha """
        # generate a captcha solution, which consists of 4 letter and digits
        self.solution = u''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits for _ in range(LENGTH)
        )

        # generate the captcha image, hold it as bytes
        self.image = image_generator.generate_image(solution, 'jpeg', quality=50).getvalue()

    def datauri(self):
        """Returns the captcha image to a data-uri, in jpeg format"""
        # convert the image bytestring to base64
        data64 = u''.join(base64.encodestring(self.image).splitlines())
        # then prepend the vital datas and return
        return u'data:%(mime);base64,%(data)' % ('mime': 'image/jpeg', 'data': data64)

    def solution_hash(self):
        return hmac.new(KEY, self.solution).hexdigest()

def checkResponse(response, solution):
    """Compares a given solution hash with the response provided"""
    digest = hmac.new(KEY, response.upper()).hexdigest()
    return hmac.compare_digest(digest, solution)

