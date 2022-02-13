from granola.tests.conftest import query_device
from granola.utils import int_to_char


def test_canned_query_should_return_valid_response(mock_cereal):
    # Given a mock pyserial class is initialized with base cereal commands
    reset_cmd = "reset"

    for _ in range(0, 10):
        # When we write the command show one or more times
        reset = query_device(mock_cereal, reset_cmd)

        # Then we get the same device information back
        true_reset = b"OK\r>"
        assert true_reset == reset


def test_unsupported_commands_return_error(mock_cereal):
    # Given a mock pyserial class is initialized with base cereal commands
    true_post = b"ERROR\r>"
    post_cmd = "incorrect command"

    # When we write a command not supported by the firmware
    post = query_device(mock_cereal, post_cmd)

    # Then ERROR is returned
    assert true_post == post


def test_multipart_writes_with_canned_queries_only_fire_on_carriage_return(mock_cereal):
    # Given a mock cereal device and write and expected response
    input = b"start"
    output = b"OK\r>"

    # When we sent the command in pieces
    for int_ in bytes(input):
        mock_cereal.write(int_to_char(int_))
        # Then the no result is produces until the write terminator is sent
        assert len(mock_cereal._next_read) == 0
    # And when the terminator is sent
    mock_cereal.write(b"\r")

    # Then the correct result,and only the correct result is returned
    assert mock_cereal.read(1000) == output
