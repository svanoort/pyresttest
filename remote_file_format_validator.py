import pyresttest.validators as validators
from pyresttest.binding import Context
import sys

# Python 3 compatibility
if sys.version_info[0] > 2:
    from past.builtins import basestring

if sys.version_info[0] > 2:
    from io import BytesIO
else:
    from StringIO import StringIO
from pyresttest.six import text_type
from pyresttest.six import binary_type
import pycurl
import certifi
import magic

class RemoteFileFormatValidator(validators.AbstractValidator):
    """ Does extract and test from request body """
    name = 'RemoteFileFormatValidator'
    extractor = None
    test_fn = None
    test_name = None
    config = None
    contains_str = None

    def get_readable_config(self, context=None):
        """ Get a human-readable config string """
        return "Extractor: " + self.extractor.get_readable_config(context=context)

    @staticmethod
    def parse(config):
        output = RemoteFileFormatValidator()
        config = validators.parsing.lowercase_keys(validators.parsing.flatten_dictionaries(config))
        output.config = config
        extractor = validators._get_extractor(config)
        output.extractor = extractor

        if 'test' not in config:  # contains if unspecified
            test_name = 'contains'
        else:
            test_name = config['test']

        output.test_name = test_name
        test_fn = VALIDATOR_TESTS[test_name]
        output.test_fn = test_fn

        if test_name == 'contains':
            try:
                output.contains_str = config['contains']
            except KeyError:
                raise ValueError(
                    "No string value found when using contains test.")

        return output

    def validate(self, body=None, headers=None, context=None):
        try:
            extracted = self.extractor.extract(
                body=body, headers=headers, context=context)
        except Exception as e:
            trace = validators.traceback.format_exc()
            return validators.Failure(message="Exception thrown while running extraction from body", details=trace, validator=self, failure_type=validators.FAILURE_EXTRACTOR_EXCEPTION)

        if self.test_name == 'contains':
            tested = self.test_fn(extracted, self.contains_str)
        else:
            tested = self.test_fn(extracted)
        if tested:
            return True
        else:
            failure = validators.Failure(details=self.get_readable_config(
                context=context), validator=self, failure_type=validators.FAILURE_VALIDATOR_FAILED)
            failure.message = "Extract and test validator failed on test: {0}({1})".format(
                self.test_name, extracted)
            # TODO can we do better with details?
            return failure

def getFileFormat(url):
    if sys.version_info[0] > 2:
        buffer = BytesIO()
    else:
        buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(pycurl.CAINFO, certifi.where())
    c.setopt(c.RANGE, "0-200")
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    return magic.from_buffer(buffer.getvalue()).encode('utf-8')

def test_is_mp4(url):
    fileFormat = getFileFormat(url)
    return ("MP4" in fileFormat)

def test_is_webm(url):
    fileFormat = getFileFormat(url)
    return ("WebM" in fileFormat)

def test_is_ogg(url):
    fileFormat = getFileFormat(url)
    return ("Ogg" in fileFormat)

def test_is_3gp(url):
    fileFormat = getFileFormat(url)
    return ("3GPP" in fileFormat)

def test_is_wma(url):
    fileFormat = getFileFormat(url)
    return ("Microsoft ASF" in fileFormat)

def test_is_mp3(url):
    fileFormat = getFileFormat(url)
    return ("MPEG" in fileFormat) and ("layer III" in fileFormat)

def test_is_flv(url):
    fileFormat = getFileFormat(url)
    return ("Flash Video" in fileFormat)

def test_is_jpg(url):
    fileFormat = getFileFormat(url)
    return ("JPEG" in fileFormat)

def test_is_png(url):
    fileFormat = getFileFormat(url)
    return ("PNG" in fileFormat)

def test_is_gif(url):
    fileFormat = getFileFormat(url)
    return ("PNG" in fileFormat)

def test_contains(url, input):
    fileFormat = getFileFormat(url)
    return (input in fileFormat)

# This is where the magic happens, each one of these is a registry of
# validators/extractors/generators to use
VALIDATORS = {'remote_file_format': RemoteFileFormatValidator.parse}
VALIDATOR_TESTS = {
    'contains': lambda x, y: test_contains(x, y),
    'is_mp3': test_is_mp3, 
    'is_mp4': test_is_mp4, 
    'is_wma': test_is_wma,
    'is_3gp': test_is_3gp,
    'is_webm': test_is_webm, 
    'is_flv': test_is_flv, 
    'is_ogg': test_is_ogg,
    'is_jpg': test_is_jpg,
    'is_png': test_is_png,
    'is_gif': test_is_gif
}
