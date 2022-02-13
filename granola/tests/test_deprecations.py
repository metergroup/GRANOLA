from granola import Cereal
from granola.tests.conftest import query_device, decode_response, CONFIG_PATH
from granola.tests.conftest import check_deprecation


@check_deprecation("Instantiating Cereal with `config_path` and `config_key`")
def test_config_key_deprecation():
    # Given 2 mock serials using deprecated config_key style instantiation
    mock1 = Cereal("just_getters_and_setters", CONFIG_PATH)
    mock2 = Cereal(config_key="just_getters_and_setters", config_path=CONFIG_PATH)

    # When we set the serial number
    for new_sn, mock in enumerate([mock1, mock2]):
        new_sn = str(new_sn)
        query_device(mock, "set -sn %s" % new_sn)
        sn = query_device(mock, "get -sn")

        # Then it should still work even though it has been deprecated
        decoded_sn = decode_response(sn, mock)
        assert new_sn + "\r>" == decoded_sn


@check_deprecation("canned_queries['data'] key '_default_csv_'")
def test_default_df_key_deprecation():
    # Given a mock serial with deprecated "files" and "_default_csv_" keys
    config = {"canned_queries": {"files": {"_default_csv_": {"1\r": "1", "2\r": {"response": "2"}}}, "delay": 0}}
    # When we initialize it, internally these keys are remapped to the non deprecated version
    mock = Cereal(config=config)()

    one = query_device(mock, "1")
    two = query_device(mock, "2")

    # Then it should still work as expected
    assert one == b"1"
    assert two == b"2"


@check_deprecation("'getters_and_setters' variable declaration follows old format")
def test_jinja2_variable_start_and_end_deprecation():
    # Given a mock serial that passes config path and key in directly and old pre-jinja variable identifiers

    # When we initialize it, internally the variable identifiers are remapped to jinja ones
    mock = Cereal(config_key="incorrect_jinja_template_for_deprecation", config_path=CONFIG_PATH)

    sn = query_device(mock, "get -sn")

    # Then it should still work as expected
    assert sn == b"42\r>"


@check_deprecation("Using 'getter' key inside 'getter_and_setters'", "Using 'setter' key inside 'getter_and_setters'")
def test_getter_and_setter_keys_deprecation():
    # Given a mock serial with "getter" and "setter" keys
    config = {
        "getters_and_setters": {
            "default_values": {"sn": "42"},
            "getters": [{"getter": "get -sn\r", "response": "{{ sn }}\r>"}],
            "setters": [{"setter": "set -sn {{ sn }}\r", "response": "OK\r>"}],
        }
    }
    # When we initialize it, internally these keys are remapped to the non deprecated version
    mock = Cereal(config=config)()

    sn = query_device(mock, "get -sn")

    # Then it should still work as expected
    assert sn == b"42\r>"


config = {"canned_queries": {"data": {"`DEFAULT`": {"1\r": "1", "2\r": ["2a", "2b"]}}}}
