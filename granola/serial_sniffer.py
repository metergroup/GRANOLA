import csv
import logging
from builtins import bytes
from builtins import (
    str as unicode,  # python 3 doesn't have a unicode type, and we don't want to override python2 str type
)
from contextlib import contextmanager
from datetime import datetime

from serial import Serial

from granola.utils import (
    IS_PYTHON3,
    add_created_at,
    check_min_package_version,
    decode_bytes,
    encode_escape_char,
    get_path,
    is_terminated_with,
    make_path,
)

logger = logging.getLogger(__name__)


class SerialSniffer(Serial):
    """
    This class is meant to be injected in place of Serial in some code that communicates with a device.
    It will then write out any serial commands sent, and their responses to a CSV file, to be used by GRANOLA.
    This code assumes that the next write after any read will be the "response"
    unpaired reads and writes will be ignored.

    Args: (passed by subclassing SerialSniffer with the appropriate class variable overwritten)
        outfile (str): Path to the file you want to write to
        delimiter : passed to csv.writer()
        quotechar : passed to csv.writer()
        write_terminator (str) : The character sequence used to indicate that a serial command is complete
        read_terminator (str) : The character sequence used to indicate that a serial response is complete

    .. todo::

        Change how this is done to the same way the Breakfast Cereal is done (init then __call__)
    """

    outfile = ""
    delimiter = ","
    quotechar = '"'
    write_terminator = b"\r"
    read_terminator = b"\r>"

    @add_created_at
    def __init__(self, *args, **kwargs):
        logger.debug("%s initializing Sniffer with Serial args %s and kwargs %s", self.__class__.__name__, args, kwargs)
        super(SerialSniffer, self).__init__(*args, **kwargs)
        if self.outfile == "":
            if self.port is not None:
                self.outfile = datetime.now().strftime("%Y-%m-%dT%H-%M-%S") + "_" + self.port + ".csv"
            else:
                self.outfile = datetime.now().strftime("%Y-%m-%dT%H-%M-%S") + "_serial_commands.csv"

        self.outpath = get_path(self.outfile)
        make_path(self.outpath)

        logger.debug("%s outpath: %s", self, self.outpath)

        self.current_write = b""
        self.current_read = b""
        self.last_write_time = datetime.now()
        self.last_read_time = datetime.now()

        try:
            with _open_csv_writer(
                self.outpath, "w", delimiter=self.delimiter, quotechar=self.quotechar, quoting=csv.QUOTE_MINIMAL
            ) as csvwriter:
                csvwriter.writerow(["cmd", "response", "delay(ms)"])
        except IOError as err:
            logger.exception("%s %r", self, err)

    def __str__(self):
        port = getattr(self, "port", "")
        port_str = " on %s" % port if port else ""
        return "{device}{port}".format(device=self.__class__.__name__, port=port_str)

    def write(self, data, *args, **kwargs):
        """
        A wrapper for Serial.write, that also stores written content, and when a terminator is reached,
        records that read to the given csv inputs and outputs are the same as Serial.read
        Note: to mock the behavior of the serial instruments I have access to, any charaters after the initial
        terminator are ignored for our purposes. They are still written to the serial port, of course."""

        logger.info("%s write: %r", self, data)

        if not self._is_write_terminated(self.current_write):
            # this write is not yet terminated
            for int_repr in bytes(data):  # convert byte data into ascii int representation
                self.current_write += bytes([int_repr])  # convert back to bytes
                if self._is_write_terminated(self.current_write):
                    self.last_write_time = datetime.now()
                    self.current_read = b""
                    break

        return super(SerialSniffer, self).write(data, *args, **kwargs)

    def read(self, size=1, *args, **kwargs):
        """
        A wrapper for Serial.read, that also stores read content, and when a terminator is reached,
        records that read to the given csv inputs and outputs are the same as Serial.read"""
        read = super(SerialSniffer, self).read(size=size, *args, **kwargs)

        logger.info("%s read: %r", self, read)

        self.current_read += read

        if self._is_read_terminated(self.current_read):
            self.last_read_time = datetime.now()
            delay = (self.last_read_time - self.last_write_time).total_seconds() * 1000
            try:
                if self._is_write_terminated(self.current_write):
                    with _open_csv_writer(
                        self.outpath, "a", delimiter=self.delimiter, quotechar=self.quotechar, quoting=csv.QUOTE_MINIMAL
                    ) as csvwriter:
                        csvwriter.writerow(
                            [
                                encode_escape_char(decode_bytes(self.current_write)),
                                encode_escape_char(decode_bytes(self.current_read)),
                                delay,
                            ]
                        )
            except IOError as err:
                logger.exception("%s %r", self, err)
            self.current_write = b""
            self.current_read = b""

        return read

    if check_min_package_version("pyserial", "3.0"):

        def reset_input_buffer(self):
            """
            A wrapper for serial.reset_input_buffer that also clears the current read buffer.
            Should only be used with pyserial versions >= 3.0"""
            self.current_read = b""
            super(SerialSniffer, self).reset_input_buffer()

        def reset_output_buffer(self):
            """
            A wrapper for serial.reset_output_buffer that also clears the current write buffer.
            Should only be used with pyserial versions >= 3.0"""
            self.current_write = b""
            super(SerialSniffer, self).reset_output_buffer()

    else:

        def flushInput(self):
            """
            A wrapper for serial.FlushInput that also clears the current read buffer.
            Should only be used with pyserial versions <= 3.0"""
            self.current_read = b""
            super(SerialSniffer, self).flushInput()

        def flushOutput(self):
            """
            A wrapper for serial.FlushOutput that also clears the current write buffer.
            Should only be used with pyserial versions <= 3.0"""
            self.current_write = b""
            super(SerialSniffer, self).flushOutput()

    def _is_write_terminated(self, input):
        return is_terminated_with(input, self.write_terminator)

    def _is_read_terminated(self, input):
        return is_terminated_with(input, self.read_terminator)


@contextmanager
def _open_csv_writer(path, mode, **kwargs):
    """
    A contextmanager to open the csv file at a given path (in either python 2 or 3) and return a writer object
    for that file

    Args:
        path (str): the path to your csv file
        mode (str): the access mode passed on to open
        additional **kwargs are passed to csv.writer()

    Returns:
        csv.writer: a handle for the csv writer
    """

    if IS_PYTHON3:
        csvfile = open(path, mode, newline="")
    else:
        csvfile = open(path, mode + "b")
        kwargs = {
            k: str(v) if isinstance(v, unicode) else v  # python 2 csv writer needs byte strings
            for k, v in kwargs.items()
        }

    csvwriter = csv.writer(csvfile, **kwargs)
    try:
        yield csvwriter
    finally:
        csvfile.close()


__doc__ = """
``SerialSniffer`` is a class that can be used in place of pyserial Serial to track every write and read for pyserial.
All it does is capture every incoming write and read, writes it out to a csv, and then passes it along to
pyserial.

You can easily run ``SerialSniffer`` in your code for a one off to just capture some commands for mocking later
by replacing your pyserial Serial import with::

    from granola import SerialSniffer as Serial
"""
