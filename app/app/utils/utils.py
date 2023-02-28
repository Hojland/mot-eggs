import asyncio
import base64
import quopri
import re
import signal
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime

import pytz
from loguru import logger


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if "log_time" in kw:
            name = kw.get("log_name", method.__name__.upper())
            kw["log_time"][name] = int((te - ts) * 1000)
        else:
            logger.debug("%r  %2.2f ms" % (method.__name__, (te - ts) * 1000))
        return result

    return timed


def async_timeit(method):
    async def process(func, *args, **kw):
        if asyncio.iscoroutinefunction(method):
            return await func(*args, **kw)
        else:
            return method(*args, **kw)

    async def helper(*args, **kw):
        ts = time.time()
        result = await process(method, *args, **kw)
        te = time.time()
        if "log_time" in kw:
            name = kw.get("log_name", method.__name__.upper())
            kw["log_time"][name] = int((te - ts) * 1000)
        else:
            logger.info("%r  %2.2f ms" % (method.__name__, (te - ts) * 1000))
        return result

    return helper


def time_now(local_tz: pytz.timezone = None):
    if not local_tz:
        local_tz = pytz.timezone("Europe/Copenhagen")
    now = datetime.today().replace(tzinfo=pytz.utc).astimezone(tz=local_tz)
    return now


def try_decode(text: str, char_encoding: str = "UTF-8"):
    try:
        content_str = str(text, char_encoding)
        content_str = unicodedata.normalize("NFKD", content_str)
    except:
        try:
            content_str = text.decode("unicode_escape").encode("utf8").decode("utf8")
            content_str = unicodedata.normalize("NFKD", content_str)
        except:
            try:
                content_str = text.decode("ISO 8859-1")
                content_str = unicodedata.normalize("NFKD", content_str)
            except:
                raise ValueError("couldn't decode")
    return content_str


def flatten_list(l: list):
    flat_list = [item for sublist in l for item in sublist]
    return flat_list


def decode_filename(filename: str) -> str:
    """
    This function applies a regular expression to pull out the character set, encoding, and encoded text from the
    encoded words. Next, it decodes the encoded words into a byte string, using either the quopri module or base64
    module as determined by the encoding. Finally, it decodes the byte string using the character set and returns the
    result.
    """
    try:
        encoded_word_regex = r"=\?{1}(.+)\?{1}([B|Q])\?{1}(.+)\?{1}="
        charset, encoding, encoded_text = re.match(encoded_word_regex, filename).groups()
        if encoding == "B":
            byte_string = base64.b64decode(encoded_text)
        elif encoding == "Q":
            byte_string = quopri.decodestring(encoded_text)
        return try_decode(byte_string, charset)

    except Exception as e:
        logger.debug(f"Error when decoding filename with: {e}")
        return filename


@contextmanager
def timeout(seconds: int = 10):
    """timeouts a hanging function after specified time period
    Args:
        timeout_sec (int, optional): [Period in seconds for time until timeout]. Defaults to 10.
    """

    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)  # Ten seconds
    try:
        yield
    except TimeoutException:
        raise TimeoutException(f"Timed out after {seconds} seconds!")
    finally:
        # if the action ends in specified time, timer is canceled
        signal.alarm(0)  # signal.signal(signal.SIGALRM, signal.SIG_IGN)


class TimeoutException(Exception):
    def __init__(self, *args, **kwargs):
        pass