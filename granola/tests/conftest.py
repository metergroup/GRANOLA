import functools
import os
import warnings

import pytest

from granola import Cereal, SerialSniffer
from granola.utils import IS_PYTHON3

if IS_PYTHON3:
    from unittest.mock import patch
else:
    from mock import patch

current_dir = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = os.path.join(current_dir, "config.json")


def assert_filled_all(mask):
    assert not mask.empty
    assert mask.all()


def assert_filled_any(mask):
    assert not mask.empty
    assert mask.any()


def query_device(bk_cereal, cmd):
    bk_cereal.write(("{cmd}\r".format(cmd=cmd)).encode(bk_cereal._encoding))
    return bk_cereal.read(1000)


def decode_response(response, bk_cereal):
    return response.decode(bk_cereal._encoding)


def check_deprecation(*msgs):
    if callable(msgs[0]):
        func = msgs[0]
        msg = "deprecated"

        @functools.wraps(func)
        def _inner(*args, **kwargs):
            with warnings.catch_warnings(record=True) as w:
                r = func(*args, **kwargs)
                assert issubclass(w[-1].category, Warning)
                assert msg in str(w[-1].message).lower()
            return r

        return _inner
    else:

        def _check_deprecation(func):
            @functools.wraps(func)
            def _inner(*args, **kwargs):
                with warnings.catch_warnings(record=True) as w:
                    r = func(*args, **kwargs)
                    found_warning = False
                    for msg in msgs:
                        for warning in w:
                            if issubclass(warning.category, Warning) and msg.lower() in str(warning.message).lower():
                                found_warning = True
                                break
                        assert found_warning
                return r

            return _inner

        return _check_deprecation


class SerialSnifferTester(SerialSniffer):
    outfile = "test_output.csv"


@pytest.fixture
def mock_cereal():
    return Cereal.mock_from_file("cereal", config_path=CONFIG_PATH)()


@pytest.fixture
def bk_cereal_only_getters_and_setters():
    return Cereal.mock_from_file("just_getters_and_setters", config_path=CONFIG_PATH)()


@pytest.fixture
def sniff_sniff():
    sniff = SerialSnifferTester()
    yield sniff
    os.remove(sniff.outpath)


@pytest.fixture
def mock_write():
    with patch("serial.Serial.write") as write:
        yield write


@pytest.fixture
def mock_read():
    with patch("serial.Serial.read") as read:
        yield read


@pytest.fixture
def canned_queries_config():
    canned_queries = {
        "canned_queries": {
            "data": {
                "`DEFAULT`": {
                    "1\r": "1",
                    "2\r": {"response": "2"},
                    "3\r": {"response": "3", "delay": 3},
                    "4\r": {"response": ["4a", "4b"]},
                    "5\r": {"response": ["5a", "5b"], "delay": 5},
                    "6\r": {"response": ["6a", "6b"], "delay": [6.1, 6.2]},
                    "7\r": {"response": [["7a", {"delay": 7}], "7b"]},
                    "8\r": {"response": [["8a", {"delay": 8.1}], "8b"], "delay": 8},
                    "9\r": [["9a", {"delay": 9}], "9b"],
                }
            },
            "delay": 0,
        }
    }
    return canned_queries
