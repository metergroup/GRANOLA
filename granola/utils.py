import abc
from datetime import datetime
import functools
import logging
import os
import pathlib
import sys
import warnings
from builtins import (
    bytes,
    str as unicode,  # python 3 doesn't have a unicode type, and we don't want to override python2 str type
)
from collections import OrderedDict

import pandas as pd
import pkg_resources

logger = logging.getLogger(__name__)

IS_PYTHON3 = sys.version_info >= (3, 0, 0)

PYSERIAL_FIELDS_TO_EXCLUDE = {"BAUDRATES", "BYTESIZES", "STOPBITS", "PARITIES", "portstr", "writeTimeout"}

SENTINEL = object()

# making ABCs more uniform and compatible between python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {})


def add_created_at(init):
    """
    init decorator that adds `_created_at` attribute. May add future functionality later"""
    @functools.wraps(init)
    def wrapper(self, *args, **kwargs):
        init(self, *args, **kwargs)
        self._created_at = datetime.now()
    return wrapper


def fixpath(path):
    r"""
    On a linux like system (Posix system), it can't handle windows file pathing,
    this is a way to resolve that.
    On a linux system it first converts it to a windows path (where it handles both \ and /, thus
    reading it as a valid path), and then when it is a valid path, convert it back to a linux path.
    On a windows system, it is just happy to read it as a pathlib.Path (which will use either a
    WindowsPath on windows systems) since \, /, and \\ are fine.

    We then make sure to return a string.
    """
    if os.name == 'posix':
        new_path = pathlib.PureWindowsPath(path).as_posix()
    else:
        new_path = pathlib.Path(path)
    return str(new_path)


def deunicodify_hook(pairs):
    """Hook for ``json.load`` to convert unicode json to byte json for python 2"""
    new_pairs = []
    for key, value in pairs:
        if isinstance(value, list):
            value = [val.encode('utf-8') if isinstance(val, unicode) else val for val in value]
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        new_pairs.append((key, value))
    return OrderedDict(new_pairs)


def decode_bytes(byte_string):
    """Helper function to decode a bytestring"""
    if isinstance(byte_string, bytes):
        if IS_PYTHON3:
            return byte_string.decode("unicode_escape")
        else:
            return byte_string.decode('string_escape')
    raise TypeError('unicode strings are not supported, only use byte strings: {!r}'.format(byte_string))


def encode_to_bytes(string, encoding="ascii"):
    """Helper function to encode a string as a bytestring"""
    if not isinstance(string, bytes):
        string = string.encode(encoding)
    return string


def decode_escape_char(string):
    """Helper function to decode escape character from either a string or a byte string"""
    if IS_PYTHON3:
        return bytes(string, "utf-8").decode("unicode_escape")
    else:
        return string.decode('string_escape')


def encode_escape_char(string):
    """Helper function to encode escape characters and non-unicode for printing to csv"""

    if IS_PYTHON3 or isinstance(string, unicode):
        return unicode(string.encode("unicode_escape"), "utf-8")
    else:
        return string.encode('string_escape')


def load_serial_df(path):
    """
    Load CSV into DataFrame.

    Necessary columns -> cmd, response
    """

    df = pd.read_csv(path,
                     converters=dict(cmd=decode_escape_char,
                                     response=decode_escape_char),
                     skipinitialspace=True)
    return df


def check_min_package_version(package, minimum_version, should_trunc_to_same_len=True):
    """Helper to decide if the package you are using meets minimum version requirement for some feature."""
    real_version = pkg_resources.get_distribution(package).version
    if should_trunc_to_same_len:
        minimum_version = minimum_version[0:len(real_version)]

    logger.debug("package %s, version: %s, minimum version to run certain features: %s",
                 package, real_version, minimum_version)

    return real_version >= minimum_version


def get_path(path):
    """
    Helper function that if you pass in a path to a file, returns the absolute path.
    If the directory to that path does not exist, then it makes all the directories needed.

    Args:
        path (str): path to file

    Returns:
        str: absolute path to file
    """
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.isdir(dir_name):  # TODO (madeline) make the makedirs into its own function?
        os.makedirs(dir_name)
    return os.path.abspath(path)


def int_to_char(int_):
    """Return an ascii character in byte string form for a given int"""
    return bytes([int_])


def is_terminated_with(input, terminator):
    """
    Helper to check if a given input has ends with the given terminator

    Args:
        input(str): the input to check
        terminator(str): some termination sequence

    Returns:
        bool : whether the input ends with the terminator
        """
    if len(input) < len(terminator):
        return False
    else:
        return input[-len(terminator):] == terminator


def _get_subclasses(cls):
    return {subclass.__name__: subclass for subclass in cls.__subclasses__()}


def deprecation(message):
    warnings.simplefilter('always', DeprecationWarning)
    warnings.warn(message, DeprecationWarning)
