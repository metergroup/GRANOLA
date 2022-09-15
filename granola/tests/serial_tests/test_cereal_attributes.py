import pytest

from granola import PortNotOpenError
from granola.utils import check_min_package_version


def test_fixture_communication_device_should_start_open(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When the class is initialized

    # Then it should start open
    assert mock_cereal._is_open


def test_fixture_communication_device_closing_conn_should_return_closed(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we close the connection
    mock_cereal.close()

    # Then it should be close
    assert not mock_cereal._is_open


def test_fixture_communication_device_opening_conn_should_return_open(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we take an initialized mock serial class (open) and open it
    mock_cereal.open()

    # Then it should stay open
    assert mock_cereal._is_open


def test_fixture_communication_device_closing_conn_then_opening_should_return_open(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we close and reopen the connection
    mock_cereal.close()
    mock_cereal.open()

    # Then the connection should be open
    assert mock_cereal._is_open


def test_fixture_should_raise_portnotopenerror_if_used_while_closed(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When we close the connection
    mock_cereal.close()

    # Then we shouldn't be able to query the device
    with pytest.raises(PortNotOpenError):
        mock_cereal.write("get ver\r")


def test_fixture_should_raise_portnotopenerror_if_used_while_closed_but_then_open_and_try_again(mock_cereal):
    # Given a mock pyserial class has been initialized

    # When you close and reopen the connection
    mock_cereal.close()
    try:
        mock_cereal.write(b"get -ver\r")
    except PortNotOpenError:
        pass
    mock_cereal.open()

    # and then we write to the mock device
    mock_cereal.write(b"get -ver\r")

    # Then we should be able to get a response
    response = mock_cereal.read()
    assert response


def test_flush_input(mock_cereal):
    # Given a mock serial device with some unread data
    mock_cereal.write(b"get -ver\r")

    # When you call flush input in the appropriate pyserial version
    if check_min_package_version("pyserial", "3.0"):
        assert mock_cereal.in_waiting > 0
        mock_cereal.reset_input_buffer()

        # Then the read buffer is cleared
        assert mock_cereal.in_waiting == 0
    else:
        assert mock_cereal.inWaiting() > 0
        mock_cereal.flushInput()

        # Then the read buffer is cleared
        assert mock_cereal.inWaiting() == 0


def test_flush_output(mock_cereal):
    # Given a mock serial device with som write data, but no CR
    mock_cereal.write(b"get -ver")

    assert len(mock_cereal._next_write) > 0

    # When you call flush output
    if check_min_package_version("pyserial", "3.0"):
        mock_cereal.reset_output_buffer()  # defined for pyserial versions >= 3.0
    else:
        mock_cereal.flushOutput()  # defined for pyserial versions < 3.0

    # Then write buffer is cleared
    assert mock_cereal._next_write == ""


def test_reconfigure_port(mock_cereal):
    # Given a mock serial device, open the port
    mock_cereal.open()
    assert mock_cereal.is_open

    # When an attribute is called that pySerial internally reconfigures the port
    mock_cereal.baudrate = 57600

    # Then the call is successful
    assert mock_cereal.baudrate == 57600
