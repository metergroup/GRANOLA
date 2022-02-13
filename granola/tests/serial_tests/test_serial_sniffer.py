import os
import time
from builtins import bytes
from datetime import datetime

from granola import SerialSniffer
from granola.utils import (
    IS_PYTHON3,
    check_min_package_version,
    decode_bytes,
    int_to_char,
    load_serial_df,
)

if IS_PYTHON3:
    from unittest.mock import patch
else:
    from mock import patch


def test_read_still_works(sniff_sniff, mock_read, return_value=b"Serial's read was called"):
    # Given a serial sniffer object

    # When we call read
    mock_read.return_value = return_value

    # Then Serial's read function runs
    assert return_value == sniff_sniff.read()


def test_write_still_works(sniff_sniff, mock_write, input=b"string\r"):
    # Given a serial sniffer object and some input string

    # When we write
    mock_write.return_value = len(input)

    # Then Serial's write function still runs
    assert sniff_sniff.write(input) == 7


def test_sniffer_with_bad_outpath_doesnt_break_serial(mock_read, mock_write):
    # Given a sniffer object with an absolute path to a file without permissions (in this case, a directory)
    class BadSniffer(SerialSniffer):
        outfile = "granola"

    # When you initialize an object and call read and write with it.
    bad_sniff = BadSniffer()
    test_read_still_works(bad_sniff, mock_read)
    test_write_still_works(bad_sniff, mock_write)

    # Then there are no uncaught exceptions and read and write still work


def test_sniffer_given_no_port_or_path_uses_default():
    # Given no com port or path

    # When you create a sniffer object at some particular time
    with patch("granola.serial_sniffer.datetime") as dt:
        dt.now.return_value = datetime(2021, 9, 17, 16, 46, 7)
        sniff_sniff = SerialSniffer()

    true_outpath = "2021-09-17T16-46-07_serial_commands.csv"
    # It creates an output file at ./[timestamp]_serial_commands.csv
    assert sniff_sniff.outpath == os.path.abspath(true_outpath)
    # and we cleanup the created sniffer file
    os.remove(sniff_sniff.outpath)


def test_sniffer_given_port_only_uses_that_path():
    # Given some comport
    com = "COM3"

    # When you create a sniffer object
    with patch("serial.Serial.open"), patch("granola.serial_sniffer.datetime") as dt:
        dt.now.return_value = datetime(2021, 9, 17, 16, 46, 7)
        sniff_sniff = SerialSniffer(com, baudrate=9600)

    # It creates a custom filename of the form [timestamp]_[port].csv
    true_outpath = "2021-09-17T16-46-07_COM3.csv"
    assert sniff_sniff.outpath == os.path.abspath(true_outpath)
    # and we cleanup the created sniffer file
    os.remove(sniff_sniff.outpath)


def test_sniffer_with_absolute_path_uses_that_path():
    # Given a sniffer object with an absolute path
    class AbsoluteSniffer(SerialSniffer):
        outfile = os.path.abspath("some_output.csv")

    # When you initialize an object with or without an associated com port
    rel_sniff_no_com = AbsoluteSniffer()
    with patch("serial.Serial.open"):
        rel_sniff_com = AbsoluteSniffer("COM3")

    # Then the output file is opened in the right directory
    try:
        assert os.path.exists(os.path.abspath("some_output.csv"))
    finally:
        # and we cleanup the created sniffer file
        os.remove(rel_sniff_no_com.outpath)

    # Then the sniffer given a comport had that same outpath, and was also cleaned up
    assert not os.path.exists(rel_sniff_com.outpath)


def test_sniffer_with_relative_path_uses_that_path():
    # Given a sniffer object with a relative path
    path = "granola/tests/some_output.csv"

    class AbsoluteSniffer(SerialSniffer):
        outfile = path

    # When you initialize an object
    abs_sniff_no_com = AbsoluteSniffer()
    with patch("serial.Serial.open"):
        abs_sniff_com = AbsoluteSniffer("COM3")

    # Then the output file is opened in the right directory
    try:
        assert os.path.exists(os.path.abspath("granola/tests/some_output.csv"))
    finally:
        # and we cleanup the created sniffer file
        os.remove(abs_sniff_no_com.outpath)

    # Then the sniffer given a comport had that same outpath, and was also cleaned up
    assert not os.path.exists(abs_sniff_com.outpath)


def test_read_write_are_recorded_and_only_produce_one_row(mock_read, mock_write, sniff_sniff):
    # Given a serial sniffer object and some command input and output
    input = b"show\r"
    output = b"Cereal 0.07.0 42\r>"

    # When we write a command and read the response
    mock_write.return_value = len(input)
    sniff_sniff.write(input)
    mock_read.return_value = output
    sniff_sniff.read()

    # Then the result is written to the csv
    result = load_serial_df(sniff_sniff.outpath)
    with open(sniff_sniff.outpath) as sniffer_out_file:
        assert len(sniffer_out_file.readlines()) == 2
    assert result["cmd"].iloc[0] == decode_bytes(input)
    assert result["response"].iloc[0] == decode_bytes(output)


def test_two_sequential_writes_and_one_read_generates_only_one_row(mock_read, mock_write, sniff_sniff):
    # Given a serial sniffer object and some command input and output
    input = b"show\r"
    output = b"Cereal 0.07.0 42\r>"

    # When we read and then write
    mock_write.return_value = len(input)
    sniff_sniff.write(input)
    sniff_sniff.write(input)
    mock_read.return_value = output
    sniff_sniff.read()

    # Then the result is written to the csv, and there are not extra rows
    result = load_serial_df(sniff_sniff.outpath)
    assert len(result) == 1
    assert result["cmd"].iloc[0] == decode_bytes(input)
    assert result["response"].iloc[0] == decode_bytes(output)


def test_one_write_and_two_sequential_reads_ignores_unmatched_outputs(mock_read, mock_write, sniff_sniff):
    # Given a serial sniffer object and some command input and output
    input = b"show\r"
    output = b"Cereal 0.07.0 42\r>"

    # When we write and then read twice
    mock_write.return_value = len(input)
    sniff_sniff.write(input)
    mock_read.return_value = output
    sniff_sniff.read()
    sniff_sniff.read()

    # Then the result is written to the csv, and there are not extra rows
    result = load_serial_df(sniff_sniff.outpath)
    assert len(result) == 1
    assert result["cmd"].iloc[0] == decode_bytes(input)
    assert result["response"].iloc[0] == decode_bytes(output)


def test_read_write_in_pieces_produces_only_one_row(mock_read, mock_write, sniff_sniff):
    # Given a serial sniffer object and some command input and output
    input = b"show\r"
    output = b"Cereal 0.07.0 42\r>"

    # When we write a command character by character and then read the response character by character
    for int_ in bytes(input):
        mock_write.return_value = 1
        sniff_sniff.write(int_to_char(int_))
    for int_ in output:
        mock_read.return_value = int_to_char(int_)
        sniff_sniff.read()

    # Then the result is written to the csv, and nothing else
    result = load_serial_df(sniff_sniff.outpath)
    assert len(result) == 1
    assert result["cmd"].iloc[0] == decode_bytes(input)
    assert result["response"].iloc[0] == decode_bytes(output)


def test_non_ascii_bytes_write_to_csv(mock_read, mock_write, sniff_sniff):
    # Given a serial sniffer object and some command with non-ascii encoded outputs
    input = b"scan\r"
    output = b"\r\x92 yv c.dxu0~q }k0\x80qf|\x7f f.by~w0q 0lu||\x94\x7fu c.dxu0~q }k0\x80qf|\x7f f 0|y~w0 q.ru||\r>"

    mock_write.return_value = len(input)
    sniff_sniff.write(input)
    mock_read.return_value = output
    sniff_sniff.read()

    # Then the result is written to the csv
    result = load_serial_df(sniff_sniff.outpath)
    with open(sniff_sniff.outpath) as sniffer_out_file:
        assert len(sniffer_out_file.readlines()) == 2
    assert result["cmd"].iloc[0] == decode_bytes(input)
    assert result["response"].iloc[0] == decode_bytes(output)


def test_clear_input_buffer(mock_write, sniff_sniff):
    # Given a serial sniffer and some input
    input = b"some garbage"

    # When you write the input and then call flush input in the appropriate version of pyserial
    mock_write.return_value = len(input)
    sniff_sniff.write(input)
    if check_min_package_version("pyserial", "3.0"):
        with patch("serial.Serial.reset_input_buffer"):
            sniff_sniff.reset_input_buffer()  # defined for pyserial versions >= 3.0
    else:
        with patch("serial.Serial.flushInput"):
            sniff_sniff.flushInput()  # defined for pyserial versions < 3.0

    # Then the current write buffer will be empty
    assert sniff_sniff.current_read == b""


def test_clear_output_buffer(mock_read, sniff_sniff):
    # Given a serial sniffer and some input
    output = b"some garbage"

    # When you read some output and then call flush output in the appropriate version of pyserial
    mock_read.return_value = output
    sniff_sniff.read(output)
    if check_min_package_version("pyserial", "3.0"):
        with patch("serial.Serial.reset_output_buffer"):
            sniff_sniff.reset_output_buffer()  # defined for pyserial versions >= 3.0
    else:
        with patch("serial.Serial.flushOutput"):
            sniff_sniff.flushOutput()  # defined for pyserial versions < 3.0

    # Then the current read buffer will be empty
    assert sniff_sniff.current_write == b""


def test_delay_recorded(mock_read, mock_write, sniff_sniff):
    # Given a serial sniffer object and some command input and output and a delay
    input = b"show\r"
    output = b"Cereal 0.07.0 42\r>"
    delay = 1

    # When we write a command and read the response
    mock_write.return_value = len(input)
    sniff_sniff.write(input)
    time.sleep(delay)
    mock_read.return_value = output
    sniff_sniff.read()

    # Then the result is written to the csv
    result = load_serial_df(sniff_sniff.outpath)
    assert result.loc[0, "delay(ms)"] >= delay * 1000


def test_reads_writes_length_of_terminator_still_behave(mock_read, mock_write, sniff_sniff):
    # Given a serial sniffer object and some command input and output
    input = b"\r"
    output = b"\r>"

    # When we read/write just the terminator
    mock_write.return_value = len(input)
    sniff_sniff.write(input)
    mock_read.return_value = output
    sniff_sniff.read()

    # Then no errors are thrown and the lines are still written
    result = load_serial_df(sniff_sniff.outpath)
    assert result["cmd"].iloc[0] == decode_bytes(input)
    assert result["response"].iloc[0] == decode_bytes(output)
