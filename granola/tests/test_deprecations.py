from granola import MockSerial
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
    "command_readers['CannedQueries']['data'] key '_default_csv_' has been deprecated, Use '`DEFAULT`' instead"
)
def test_default_df_key_deprecation():
    # Given a mock serial with deprecated "files" and "_default_csv_" keys
    mock = MockSerial("deprecated", CONFIG_PATH_DEPRECATIONS)

    fortytwo = query_device(mock, "get -sn")

    # Then it should still work as expected
    assert fortytwo == b"42\r>"


@check_deprecation("'GettersAndSetters' variable declaration may follow old format")
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
