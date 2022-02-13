import inspect
import json
import logging
import os

from collections import OrderedDict

from serial import Serial

from granola.command_readers import GettersAndSetters, CannedQueries, BaseCommandReaders
from granola.hooks.base_hook import _run_pre_reading_hooks, _run_post_reading_hooks
from granola.hooks.base_hook import BaseHook
from granola.hooks.hooks import LoopCannedQueries
from granola.utils import (
    SENTINEL,
    decode_bytes,
    encode_to_bytes,
    fixpath,
    get_path,
    _get_subclasses,
    check_min_package_version,
    add_created_at,
    is_terminated_with,
    IS_PYTHON3,
    deunicodify_hook,
    deprecation,
)

try:
    from serial import PortNotOpenError  # for newer versions of pyserial
except ImportError:  # pragma: no cover
    PortNotOpenError = ValueError  # for pyserial 2.6


logger = logging.getLogger(__name__)


class Cereal(Serial):
    r"""
    Mock pyserial Serial class that takes CSVs of serial commands to use for mocking.
    Serial commands are routed to various CSVs based on which command is passed in.
    A serial command is checked against a dictionary of ``SerialCmds``s for if that serial command
    is a regex match to the keys in that dictionary. If it is, then it uses that CSV, if it doesn't,
    it uses the a default serial command file under the key ```DEFAULT```.

    Mock serials initialization follows a 2 step process. The first is with the normal `__init__`
    method where you pass arguments to Cereal, you can do this before your project is going,
    as part of the setup. At this point, Cereal will be able to mock but it won't have many
    pyserial Serial attributes defined such as port, baudrate. Cereal is
    then able to be "initialized" a second time, following the signature of pyserial Serial class.
    This allows you to setup Cereal with its configuration before and, and then not have to
    change your code that initializes Pyserial much or at all. Ways to get Cereal in place of
    Pyserial are depencency injection or monkey patching.

    The CSVs must have the columns cmd and response in them, it can have other columns as well.

    Args:
        config_key = (str) Which instrument in the config json to pull out for this particular mock
            serial.

        config_path: (str) Path to configuration json file. You can define multiple instruments in
            this json file. Which instrument is used for this mock serial will be the one that
            is passed in config_key.

            If you don't specify a config_path, it will default to config.json in the root directory
            of your python path.

            The key "canned_queries" (optional) is a dictionary of csv files of serial
            cmd and responses. inside "canned_queries", and then put
            another dictionary with all the files where the keys are regexes to map incoming
            serial commands to the CSVs and the values are paths to those CSVs. The CSV path with
            the key "`DEFAULT`" will be the default csv looked in if a serial command comes in
            and doesn't match any regex.

            The key "unsupported_response" (optional, defaults to Unsupported\r>) defines the
            response when passed into the mock serial device that is not defined.

            The key "encoding" (optional, defaults to ascii), defines what encoding and decoding
            to use.

            The key "getters_and_setters" (optional) defines the getters and setters. See `GettersAndSetters`
            for more information on formatting for those keys. Also examples are given in the
            config.json
    """

    @add_created_at
    def __init__(self, config=None, config_path=None, command_readers=None, hooks=None, config_key=None):

        self._config_path = config_path if config_path is not None else os.path.join(os.getcwd(), "config.json")

        config = self._check_and_normalize_config_deprecation(config, config_key)

        hooks = hooks if hooks is not None else []
        if command_readers is None:  # Set default command readers and hooks
            command_readers = (GettersAndSetters(), CannedQueries())
            if not hooks:
                hooks.append(LoopCannedQueries())

        self._config = config
        self._unsupported_response = self._config.get("unsupported_response", "Unsupported\r>")
        self._encoding = self._config.get("encoding", "ascii")
        self._write_terminator = "\r"  # TODO madeline, make this something to pass in from config.

        self._readers = self._setup_command_readers(command_readers, hooks)

        self._hooks = []
        self._next_read = ""  # The next read for this "serial" device
        self._next_write = ""  # The current write buffer to the serial device

        if check_min_package_version("pyserial", "3.0"):  # mocking pyserial is_open/_isOpen for different pyserials
            self.is_open = True
        else:
            self._isOpen = True

    @classmethod
    def mock_from_file(cls, config_key, config_path="config.json", *args, **kwargs):
        config = cls._load_config(config_key=config_key, config_path=config_path)
        return cls(config=config, config_path=config_path, *args, **kwargs)

    @classmethod
    def _load_config(cls, config_key, config_path):
        """
        Load configuration dictionary based on self._config_key class variable

        Loads CSV files into self.serial_cmd_files.

        If you don't pass in where self._config_path is, it will default to "config.json" in the
            root directory of your python path.
        """
        path = get_path(config_path)
        config_path = fixpath(path)

        logger.debug("%s config path: %s", cls.__name__, config_path)
        logger.debug("%s config key: %s", cls.__name__, config_key)

        with open(config_path) as f:
            if IS_PYTHON3:
                config = json.load(f, object_pairs_hook=OrderedDict)
            else:
                config = json.load(f, object_pairs_hook=deunicodify_hook)
        config = config[config_key]
        return config

    def __call__(self, *args, **kwargs):
        if not hasattr(self, "_port"):

            logger.debug("%s initializing Mock Serial with Serial args %s and kwargs %s", self, args, kwargs)

            is_open = self._is_open
            super(Serial, self).__init__(*args, **kwargs)
            self._is_open = is_open  # reset the port back to open since pyserial will close it on a dummy mock port
        else:
            raise TypeError("{cls} object is not callable".format(cls=self.__class__))

        return self

    def __str__(self):
        port = getattr(self, "port", "")
        port_str = " on %s" % port if port else ""
        return "{device}{port}".format(device=self.__class__.__name__, port=port_str)

    def read(self, size=1):
        """Mock pyserial.Serial `read`. Return number of bytes in self._next_read based on `size`"""
        read = bytearray()
        if size > 0:
            self._next_read = encode_to_bytes(self._next_read, self._encoding)
            while len(read) < size and len(self._next_read):
                read.append(self._next_read[0])
                self._next_read = self._next_read[1:]
        read = bytes(read)

        logger.info("%s read: %r", self, read)

        return read

    def write(self, data):
        """
        Mock pyserial.Serial `write` by seeding a serial command generator

        Args:
            data (byte_str): serial command
        """
        logger.info("%s write: %r", self, data)

        self._verify_open()

        data = decode_bytes(data)

        for d in data:
            self._next_write += d
            if is_terminated_with(self._next_write, self._write_terminator):
                # Based on observation, writes with multiple carriage returns only return the result up to the first
                # So data after the first terminator is basically ignored

                next_read = None
                _run_pre_reading_hooks(hooked=self, data=self._next_write)

                for reader in self._readers.values():
                    next_read = reader.get_reading(data=self._next_write)
                    if next_read is not None:
                        self._next_read = next_read
                        break

                if next_read is None or next_read is SENTINEL:
                    self._next_read = self._unsupported_response
                    # If a response is not handled by the hooks and returns SENTINEL, return unsupported with warning
                    if next_read is SENTINEL:

                        logger.warning("%s unhandled response return from hooks. Defaulting to Unsupported Response!")

                self._next_write = ""  # once we grab the next read, clear the next write
        self._next_read = _run_post_reading_hooks(hooked=self, result=self._next_read, data=self._next_write)
        return len(data)

    if check_min_package_version("pyserial", "3.0"):

        def reset_input_buffer(self):
            """
            A wrapper for serial.reset_input_buffer that also clears the current read buffer.
            Should only be used with pyserial versions >= 3.0"""
            self._clear_input()

        def reset_output_buffer(self):
            """
            A wrapper for serial.reset_input_buffer that also clears the current write buffer.
            Should only be used with pyserial versions >= 3.0"""
            self._clear_output()

        @property
        def in_waiting(self):
            """mocking pyserial's in_waiting"""
            return self._in_waiting

        @property
        def out_waiting(self):
            """mocking pyserial's out_waiting"""
            return self._out_waiting

    else:

        def flushInput(self):
            """
            A wrapper for serial.FlushInput that also clears the current read buffer.
            Should only be used with pyserial versions <= 3.0"""
            self._clear_input()

        def flushOutput(self):
            """
            A wrapper for serial.FlushOutput that also clears the current write buffer.
            Should only be used with pyserial versions <= 3.0"""
            self._clear_output()

        def inWaiting(self):
            """mocking pyserial's inWaiting"""
            return self._in_waiting

        def outWaiting(self):
            """mocking pyserial's outWaiting"""
            return self._out_waiting

    @property
    def _is_open(self):
        """internal is_open so we always return the right version depending on what pyserial we have"""
        if check_min_package_version("pyserial", "3.0"):
            return self.is_open
        else:
            return self._isOpen

    @_is_open.setter
    def _is_open(self, value):
        """internal is_open so we always return the right version depending on what pyserial we have"""
        if check_min_package_version("pyserial", "3.0"):
            self.is_open = value
        else:
            self._isOpen = value

    def close(self):
        self._is_open = False

    def open(self):  # TODO madeline raise SerialException error if _port is none or if already open
        self._is_open = True

    def _clear_input(self):
        self._next_read = ""

    def _clear_output(self):
        self._next_write = ""

    @property
    def _in_waiting(self):
        return len(self._next_read)

    @property
    def _out_waiting(self):
        return 0  # Based on my observations, devices clear this buffer instantly

    def _verify_open(self):
        """
        verify if the `port` is open

        Raises:
            PortNotOpenError
        """
        if not self._is_open:
            raise PortNotOpenError

    def _setup_command_readers(self, command_readers, hooks):
        config_hooks = self._read_file_config_hooks()
        if config_hooks:
            hooks = config_hooks
        config_command_readers = self._read_file_config_command_readers()
        if config_command_readers:
            command_readers = config_command_readers

        readers = OrderedDict()
        for reader in command_readers:
            reader.initialize_config(self._config, self._config_path)

            readers[reader.__class__.__name__] = reader

        for hook in hooks:
            if inspect.isclass(hook):  # initialize uninitialized hook to their default args
                hook = hook()
            for cls in hook.hooked_classes:
                readers[cls.__name__]._hooks.append(hook)

        return readers

    def _read_file_config_from_classes(key, subkey, baseclass):
        """
        closure to generate functions that will grab ``key`` from config and then ``subkey`` is used
        to match to a subclass of ``baseclass``. This allows users to pass in classes they want to use
        for things like hooks or other things inside a configuration dictionary (JSON).

        Args:
            key (str): The outer key to look up in the config dictionary
            subkey (str): The inner key to look up in the config dictionary to find the class name
            baseclass (class): Class to check all subclasses of when you know the class name from
                ``subkey``
        """

        def _inner(self):
            config_options = self._config.get(key, [])
            subclasses = _get_subclasses(baseclass)
            classes = []
            for cls in config_options:
                if isinstance(cls, dict):
                    c = subclasses[cls.pop(subkey)]
                    c = c(**cls)
                else:
                    c = subclasses[cls]()
                classes.append(c)
            return classes

        return _inner

    _read_file_config_hooks = _read_file_config_from_classes("hooks", "hook_type", BaseHook)

    _read_file_config_command_readers = _read_file_config_from_classes(
        "command_readers", "reader_type", BaseCommandReaders
    )

    def _check_and_normalize_config_deprecation(self, config, config_key):
        if isinstance(config, str):
            config_key = config
        if config_key is not None:
            deprecation(
                "Instantiating Cereal with `config_path` and `config_key` is deprecated"
                " and will be removed in a future release."
                "\nPlease use `Cereal.mock_from_file(config_key, config_path)` instead"
            )
            config = self._load_config(config_key=config_key, config_path=self._config_path)

            # Check for old form of variable substitution pre jinja
            getters_and_setters = config.get("getters_and_setters", {})
            start_not_in = "variable_start_string" not in getters_and_setters
            end_not_in = "variable_end_string" not in getters_and_setters
            if getters_and_setters and start_not_in and end_not_in:
                deprecation(
                    "'getters_and_setters' variable declaration follows old format"
                    " that will be removed in a future release."
                    "\nEither switch to traditional jinja2 formatting ({{ var }})"
                    "\nor specify explicitly your variable_start_string and variable_end_string inside"
                    " getters and setters (ex: 'variable_start_string': '`')"
                )
                getters_and_setters["variable_start_string"] = "`"
                getters_and_setters["variable_end_string"] = "`"

        if config is None:
            raise AttributeError("Cereal __init__ requires a config dictionary")
        return config
