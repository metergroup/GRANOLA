import logging
import os
from pathlib import Path

from granola import (
    BaseCommandReaders,
    CannedQueries,
    Cereal,
    GettersAndSetters,
    HookTypes,
    SerialSniffer,
    register_hook,
)
from granola.tests.conftest import CONFIG_PATH, decode_response, query_device
from granola.utils import IS_PYTHON3

if IS_PYTHON3:
    from unittest.mock import patch
else:
    from mock import patch


def test_a_bk_cereal_on_COM1_should_print_that_it_on_COM1():
    # Given a mock pyserial class initialized on COM1 and a sniffer on COM2
    com1 = "COM1"
    com2 = "COM2"

    # When we initialize them and get their __str__s
    bk_cereal = Cereal.mock_from_json("cereal", config_path=CONFIG_PATH)(com1)
    mock_str = str(bk_cereal)
    try:
        with patch("serial.Serial.open"):
            sniffer = SerialSniffer(com2)
        sniffer_str = str(sniffer)
    finally:
        # and we cleanup the created sniffer file
        os.remove(sniffer.outpath)

    # Then it should tell us its class name on its com port
    true_mock_string = "Cereal on COM1"
    true_sniffer_string = "SerialSniffer on COM2"
    assert true_mock_string == mock_str
    assert true_sniffer_string == sniffer_str


def test_a_bk_cereal_with_no_canned_queries_should_be_fine():
    # Given a mock pyserial class defined with no canned queries in its keys

    # When we initialize it
    Cereal.mock_from_json("just_getters_and_setters", config_path=CONFIG_PATH)

    # Then it shouldn't throw any errors


def test_that_a_config_paths_work_when_cwd_is_changed():
    # Given a path to a config that is ina totally different working tree
    cwd = os.getcwd()
    try:
        os.chdir("docs")
        config_path = "../config.json"

        # When we initialize a device with canned queries
        fake_device = Cereal.mock_from_json(config_key="fake device", config_path=config_path)

        # Then The canned queries are loaded from the path relative to the config, not CWD
        assert query_device(fake_device, "reset") == b"OK\r>"

    finally:
        # and we move back to the root directory (so if this test fails we don't break a million other tests)
        os.chdir(cwd)


def test_a_bk_cereal_with_on_GettersAndSetters_command_readers_should_still_work_with_those_commands():
    # Given a mock pyserial class defined with just a GettersAndSetters command_readers
    command_readers = [GettersAndSetters]
    new_sn = "2.718"

    # When we initialize it
    mock = Cereal.mock_from_json("cereal", config_path=CONFIG_PATH, command_readers=command_readers)()
    # and issue get and set sn commands
    query_device(mock, "set -sn %s" % new_sn)
    sn = query_device(mock, "get -sn")

    # Then the serial number should be what we set it to
    true_response = new_sn + "\r>"
    decoded_sn = decode_response(sn, mock)
    assert true_response == decoded_sn


def test_a_bk_cereal_with_on_GettersAndSetters_command_readers_should_throw_error_on_bad_query():
    # Given a mock pyserial class defined with just a GettersAndSetters command_readers
    command_readers = [GettersAndSetters]

    # When we initialize it
    mock = Cereal.mock_from_json("cereal", config_path=CONFIG_PATH, command_readers=command_readers)()
    # and it is passed a query not defined
    response = query_device(mock, "dummy command")

    # Then it should return with "ERROR\r"
    decoded_response = decode_response(response, mock)
    assert "ERROR\r>" == decoded_response


def test_a_bk_cereal_with_no_command_readers_should_still_be_able_to_throw_an_unsupported_response():
    # Given a mock pyserial class defined with just a GettersAndSetters command_readers
    command_readers = [GettersAndSetters]

    # When we initialize it
    mock = Cereal.mock_from_json("cereal", config_path=CONFIG_PATH, command_readers=command_readers)()
    # and it is passed a query not defined
    response = query_device(mock, "dummy command")

    # Then it should return with "ERROR\r"
    decoded_response = decode_response(response, mock)
    assert "ERROR\r>" == decoded_response


def test_that_a_python_dictionary_config_is_just_as_good_as_json():
    # Given a mock pyserial class defined by a python dictionary configuration
    command_readers = [CannedQueries]
    command_readers = {
        CannedQueries: {
            "data": {
                "`DEFAULT`": Path(__file__).resolve().parent / "data/cereal_cmds.csv",
            }
        }
    }

    # When we initialize it
    mock = Cereal(command_readers=command_readers)()
    # and issue test off
    ok = query_device(mock, "reset")

    # Then we should get back OK
    true_response = "OK\r>"
    decoded_sn = decode_response(ok, mock)
    assert true_response == decoded_sn


def test_that_a_python_dictionary_config_lets_you_use_getters_and_setters():
    # Given a mock pyserial class defined by a python dictionary configuration of getters and setters
    command_readers = {
        "GettersAndSetters": {
            "default_values": {
                "sn": "42",
            },
            "getters": [{"cmd": "get -sn\r", "response": "{{ sn }}\r>"}],
            "setters": [{"cmd": "set -sn {{ sn }}\r", "response": "OK\r>"}],
        }
    }
    new_sn = "2.718"

    # When we initialize it
    mock = Cereal(command_readers=command_readers)()
    # and issue get and set sn commands
    query_device(mock, "set -sn %s" % new_sn)
    sn = query_device(mock, "get -sn")

    # Then the serial number should be what we set it to
    true_response = new_sn + "\r>"
    decoded_sn = decode_response(sn, mock)
    assert true_response == decoded_sn


def test_a_json_config_can_specify_a_hook___stick_hook_specifically():
    # Given a mock serial with a json config that specifies a stick hook
    bk_cereal = Cereal.mock_from_json("stick_hook", config_path=CONFIG_PATH)

    # When we query it enough to ensure it has exhausted the generator
    for _ in range(50):
        bk_cereal.write(b"scan adc30 3\r")
        bk_cereal.read(100)

    responses = set()
    # Then all future queries should be the same
    for _ in range(10):
        bk_cereal.write(b"scan adc30 3\r")
        responses.add(bk_cereal.read(100))

        assert len(responses) == 1


def test_a_json_config_can_specify_a_hook_arguments_to_exclude_a_query___stick_hook_specifically(caplog):
    # Given a mock serial with a json config that specifies a stick hook, but to exclude get -volt
    bk_cereal = Cereal.mock_from_json("stick_hook", config_path=CONFIG_PATH)

    # When we query a our excluded response past the generator
    for _ in range(10):
        with caplog.at_level(logging.WARNING):
            bk_cereal.write(b"get -volt\r")
            bk_cereal.read(100)

    # Then we capture in our log that there was an unhandled response from the hooks
    assert "unhandled response return from hooks" in caplog.text


def test_a_json_config_can_specify_command_readers_as_well():
    # Given a mock serial with a json config that specifies a CannedQueries command reader
    mock = Cereal.mock_from_json("command_readers", config_path=CONFIG_PATH)

    # When we issue a number of commands
    ok1 = query_device(mock, "reset")
    one_hund = query_device(mock, "get batt")
    ok2 = query_device(mock, "start")

    # Then none of them are unsupported
    assert ok1 == b"OK\r>"
    assert one_hund == b"100\r>"
    assert ok2 == b"OK\r>"


def test_that_you_can_pass_in_a_custom_hook_through_the_config_dict_as_a_str_and_obj():
    # Given custom hooks
    @register_hook(hook_type_enum=HookTypes.post_reading, hooked_classes=[CannedQueries])
    def hook1(self, hooked, result, data, **kwargs):
        return "01"

    @register_hook(hook_type_enum=HookTypes.post_reading, hooked_classes=[CannedQueries])
    def hook2(self, hooked, result, data, **kwargs):
        return "02"

    # and a config dictionary that references hooks by name and by the actual object
    hooks = {
        "hook1": {"attributes": ["3\r"], "include_or_exclude": "include"},
        hook2: {"attributes": ["4\r"], "include_or_exclude": "include"},
    }

    # When we initialize it and issue our serial command
    mock = Cereal(hooks=hooks)()
    zero1 = query_device(mock, "3")
    zero2 = query_device(mock, "4")

    # Then the hooks returns 01 and 02
    assert zero1 == b"01"
    assert zero2 == b"02"


def test_that_you_can_pass_in_a_custom_command_reader_through_the_config_dict_as_a_str_and_obj():
    # Given custom command readers
    class CommandReader1(BaseCommandReaders):
        def get_reading(self, data):
            if "1" in data:
                return "Command Reader1"

    class CommandReader2(BaseCommandReaders):
        def get_reading(self, data):
            if "2" in data:
                return "Command Reader2"

    # and a config dictionary that reference the command readers by name and by the actual object
    command_readers = ["CommandReader1", CommandReader2]

    # When we initialize it and issue our serial command
    mock = Cereal(command_readers=command_readers)()
    cr1 = query_device(mock, "1")
    cr2 = query_device(mock, "2")

    # Then the hooks returns b"Command Reader1" and "Command Reader2"
    assert cr1 == b"Command Reader1"
    assert cr2 == b"Command Reader2"
