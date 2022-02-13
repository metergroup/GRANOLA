import pytest

from granola import Cereal
from granola.utils import int_to_char
from granola.tests.conftest import decode_response, query_device, CONFIG_PATH


def test_get_sn_getter_from_should_default_to_42(mock_cereal):
    # Given a mock pyserial class defined with 42 as the default to get -sn\r

    # When you query query the device with get -sn
    sn = query_device(mock_cereal, "get -sn")

    # Then the serial number should be the default
    decoded_sn = decode_response(sn, mock_cereal)
    true_default = mock_cereal._config["getters_and_setters"]["default_values"]["sn"] + "\r>"
    assert true_default == decoded_sn


def test_set_sn_setter_from_should_have_a_response_of_OK(mock_cereal):
    # Given a mock pyserial class defined with 42 as the default to get -sn\r
    new_sn = "123456789"

    # When you set the sn with set -sn 123456789\r
    response = query_device(mock_cereal, "set -sn {new_sn}".format(new_sn=new_sn))

    # Then the response should match the true setter response
    true_response = "OK\r>"
    decoded_response = decode_response(response, mock_cereal)
    assert true_response == decoded_response


def test_set_sn_setter_from_should_set_sn_then_get_sn(mock_cereal):
    # Given a mock pyserial class defined with 42 as the default to get -sn\r
    new_sn = "123456789"

    # When you set the sn with set -sn 123456789\r
    query_device(mock_cereal, "set -sn {new_sn}".format(new_sn=new_sn))
    # and you get the serial number with get -sn
    sn = query_device(mock_cereal, "get -sn")

    # Then the serial number should match the new sn
    true_response = new_sn + "\r>"
    decoded_sn = decode_response(sn, mock_cereal)
    assert true_response == decoded_sn


def test_set_command_that_sets_multiple_attributes_should_set_multiple_attributes(mock_cereal):
    # Given a mock pyserial class defined with 42 as the default  sn and 0.0.0 as the default fw_ver
    new_sn = "123456789"
    new_fw = "1.1.1"

    # When you set the sn and fw to new values
    query_device(mock_cereal, "set -some dummy command {new_sn} {new_fw}".format(new_sn=new_sn, new_fw=new_fw))

    # Then the devices instrument attributes should match those new_sn and new_fw
    device_sn = mock_cereal._readers["GettersAndSetters"].instrument_attributes["sn"].value
    device_fw = mock_cereal._readers["GettersAndSetters"].instrument_attributes["fw_ver"].value
    assert new_sn == device_sn
    assert new_fw == device_fw


def test_that_a_bk_cereal_can_be_used_with_the_default_path_from_root():
    # Given a mock serial we set up from the default path

    # When we initialize it
    Cereal.mock_from_file("fake device")()
    # Then It should be fine, and nothing should error out


def test_that_a_bk_cereal_can_be_used_with_the_default_path_from_root_and_use_getters_from_that_config():
    # Given a mock serial we set up from the default path

    # When we initialize it and query from it
    default_path_serial = Cereal.mock_from_file("fake device")()
    value = query_device(default_path_serial, "get -my value")
    # or try an undefined command
    unsupported = query_device(default_path_serial, "garbage query")

    # then the returned real query should match the expected response
    decoded_value = decode_response(value, default_path_serial)
    true_value = default_path_serial._config["getters_and_setters"]["default_values"]["my_value"]
    assert true_value == decoded_value
    # and the returned unsupported response should match the expected unsupported response
    true_unsupported = b"Unsupported\r>"
    assert true_unsupported == unsupported


def test_show_as_a_getter_should_return_more_than_one_attribute(mock_cereal):
    # Given a mock pyserial class defined with default sn = 42, default fw_ver = 0.0.0, default devtype = Cereal

    # When you query query the device with show
    show = query_device(mock_cereal, "show")

    # Then show should be the default devtype fw_ver and sn
    decoded_show = decode_response(show, mock_cereal)
    true_show = "Cereal 0.0.0 42\r>"
    assert true_show == decoded_show


def test_setter_with_multiple_attributes_and_getter_to_get_those_should_see_those_changes(mock_cereal):
    # Given a mock pyserial class defined with 42 as the default  sn and 0.0.0 as the default fw_ver
    new_sn = "123456789"
    new_fw = "1.1.1"

    # When you set the sn and fw to new values
    query_device(mock_cereal, "set -some dummy command {new_sn} {new_fw}".format(new_sn=new_sn, new_fw=new_fw))
    # and then get those values with show
    show = query_device(mock_cereal, "show")

    # Then show should reflect those changes
    decoded_show = decode_response(show, mock_cereal)
    true_show = "Cereal 1.1.1 123456789\r>"
    assert true_show == decoded_show


def test_a_bk_cereal_with_no_canned_queries_should_still_be_able_to_use_getters(bk_cereal_only_getters_and_setters):
    # Given a mock pyserial class defined with no canned queries in its keys

    # When we issue get commands
    sn = query_device(bk_cereal_only_getters_and_setters, "get -sn")
    show = query_device(bk_cereal_only_getters_and_setters, "show")

    # Then the serial number should be the default and show should return the machine name, fw version, and sn
    decoded_sn = decode_response(sn, bk_cereal_only_getters_and_setters)
    decoded_show = decode_response(show, bk_cereal_only_getters_and_setters)
    true_sn = bk_cereal_only_getters_and_setters._config["getters_and_setters"]["default_values"]["sn"]
    true_fw_ver = bk_cereal_only_getters_and_setters._config["getters_and_setters"]["default_values"]["fw_ver"]

    assert true_sn + "\r>" == decoded_sn
    assert "SOMEMACHINE %s %s\r>" % (true_fw_ver, true_sn) == decoded_show


def test_a_bk_cereal_with_no_canned_queries_should_still_be_able_to_use_setters(bk_cereal_only_getters_and_setters):
    # Given a mock pyserial class defined with no canned queries in its keys
    new_sn = "2.718"

    # When we initialize it and issue set commands and get the response
    query_device(bk_cereal_only_getters_and_setters, "set -sn %s" % new_sn)
    sn = query_device(bk_cereal_only_getters_and_setters, "get -sn")

    # Then the serial number should be what we set it to
    true_response = new_sn + "\r>"
    decoded_sn = decode_response(sn, bk_cereal_only_getters_and_setters)
    assert true_response == decoded_sn


def test_a_bk_cereal_with_no_canned_queries_should_raise_an_unsupported_response_if_passed_a_query_not_defined(
    bk_cereal_only_getters_and_setters,
):
    # Given a mock pyserial class defined with no canned queries in its keys, but "ERROR\r" as the unsupported response

    # When it is passed a query not defined
    response = query_device(bk_cereal_only_getters_and_setters, "dummy command\r")

    # Then it should return with "ERROR\r"
    decoded_response = decode_response(response, bk_cereal_only_getters_and_setters)
    assert "Unsupported\r>" == decoded_response


def test_multipart_writes_with_getters_only_fire_on_carriage_return(mock_cereal):
    # Given a mock cereal device and write and expected response
    input = b"show"
    output = b"Cereal 0.0.0 42\r>"

    # When we sent the command in pieces
    for int_ in bytes(input):
        mock_cereal.write(int_to_char(int_))
        # Then the no result is produces until the write terminator is sent
        assert len(mock_cereal._next_read) == 0
    # And when the terminator is sent
    mock_cereal.write(b"\r")

    # Then the correct result,and only the correct result is returned
    assert mock_cereal.read(1000) == output


def test_incorrect_getter_will_raise_value_error():
    # Given a mock pyserial class defined a getter that doesn't reference a default value
    config_key = "incorrect_getter"

    # When you try to initialize it
    with pytest.raises(ValueError):
        Cereal.mock_from_file(config_key=config_key, config_path=CONFIG_PATH)
        # Then it should raise a value error


def test_incorrect_setter_will_raise_value_error():
    # Given a mock pyserial class defined a setter that doesn't reference a default value
    config_key = "incorrect_setter"

    # When you try to initialize it
    with pytest.raises(ValueError):
        Cereal.mock_from_file(config_key=config_key, config_path=CONFIG_PATH)
        # Then it should raise a value error
