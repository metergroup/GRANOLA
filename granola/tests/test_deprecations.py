import time

from granola import (
    ApproachHook,
    BaseCommandReaders,
    CannedQueries,
    MockSerial,
    register_hook,
)
from granola.tests.conftest import (
    CONFIG_PATH_DEPRECATIONS,
    check_deprecation,
    decode_response,
    query_device,
)


@check_deprecation("MockSerial is deprecated. Please use granola.breakfast_cereal.Cereal instead")
def test_mock_serial_deprecation():
    # Given 2 mock serials using deprecated config_key style instantiation
    mock1 = MockSerial("deprecated", config_path=CONFIG_PATH_DEPRECATIONS)
    mock2 = MockSerial(config_key="deprecated", config_path=CONFIG_PATH_DEPRECATIONS)

    # When we set the serial number
    for new_sn, mock in enumerate([mock1, mock2]):
        new_sn = str(new_sn)
        query_device(mock, "set -sn %s" % new_sn)
        sn = query_device(mock, "get -sn")

        # Then it should still work even though it has been deprecated
        decoded_sn = decode_response(sn, mock)
        assert new_sn + "\r>" == decoded_sn


@check_deprecation(
    "canned_queries['data'] as a dictionary has been deprecated."
    "\nEither use a list of files or list of dictionaries of cmds and responses instead"
)
def test_default_df_key_deprecation():
    # Given a mock serial with deprecated "files" and "_default_csv_" keys
    mock = MockSerial("deprecated", CONFIG_PATH_DEPRECATIONS)

    fortytwo = query_device(mock, "get -sn")

    # Then it should still work as expected
    assert fortytwo == b"42\r>"


@check_deprecation("'GettersAndSetters' variable declaration follows old format")
def test_jinja2_variable_start_and_end_deprecation():
    # Given a mock serial that passes config path and key in directly and old pre-jinja variable identifiers

    # When we initialize it, internally the variable identifiers are remapped to jinja ones
    mock = MockSerial(config_key="deprecated", config_path=CONFIG_PATH_DEPRECATIONS)

    sn = query_device(mock, "get -sn")

    # Then it should still work as expected
    assert sn == b"42\r>"


@check_deprecation("Using 'getter' key inside", "Using 'setter' key inside")
def test_getter_and_setter_keys_deprecation():
    # Given a mock serial with "getter" and "setter" keys
    mock = MockSerial(config_key="deprecated", config_path=CONFIG_PATH_DEPRECATIONS)

    sn = query_device(mock, "get -sn")

    # Then it should still work as expected
    assert sn == b"42\r>"


def test_passing_in_command_readers_deprecation():
    # Given a mock serial with 2 command readers, one of them custom
    class CommandReader(BaseCommandReaders):
        def get_reading(self, data):
            if "1" in data:
                return "Command Reader"

    mock = MockSerial(
        config_key="deprecated", config_path=CONFIG_PATH_DEPRECATIONS, command_readers=[CannedQueries, CommandReader]
    )

    sn = query_device(mock, "get -sn")
    one = query_device(mock, "1")

    # Then it should trigger our 2 different command readers
    assert sn == b"42\r>"
    assert one == b"Command Reader"


def test_passing_in_hook_deprecation():
    # Given a mock serial with 2 hooks, one of them custom
    @register_hook(hook_type_enum="post_reading", hooked_classes=[CannedQueries])
    def hook(self, hooked, result, data, **kwargs):
        if "1" in data:
            return "hook"
        return result

    approach_hook = ApproachHook(attributes={"temp"}, include_or_exclude="include")

    mock = MockSerial(config_key="deprecated", config_path=CONFIG_PATH_DEPRECATIONS, hooks=[approach_hook, hook])

    # When we set the temperature higher (not instantly since it is doesn't exclude temp)
    query_device(mock, "set -temp 25")
    # and then query it repeatedly
    old_value = float(query_device(mock, "get -temp")[:-2])
    for _ in range(5):
        time.sleep(0.001)
        # we grab the numeric part of the temp, leaving behind the write terminator
        new_value = float(query_device(mock, "get -temp")[:-2])

        # then each new value is strictly larger than the old value
        assert new_value > old_value

    # And when we query something with a 1
    hk = query_device(mock, "1")

    # Then it should trigger the custom hook and return "hook"
    assert hk == b"hook"
