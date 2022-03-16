import inspect
import json
import logging
import os
from collections import OrderedDict

from serial import Serial

from granola.command_readers import BaseCommandReaders, CannedQueries, GettersAndSetters
from granola.hooks.base_hook import (
    BaseHook,
    _run_post_reading_hooks,
    _run_pre_reading_hooks,
)
from granola.utils import (
    IS_PYTHON3,
    SENTINEL,
    _get_subclasses,
    add_created_at,
    check_min_package_version,
    decode_bytes,
    deunicodify_hook,
    encode_to_bytes,
    fixpath,
    get_path,
    is_terminated_with,
)

try:
    from serial import PortNotOpenError  # for newer versions of pyserial
except ImportError:  # pragma: no cover
    PortNotOpenError = ValueError  # for pyserial 2.6


logger = logging.getLogger(__name__)


class Cereal(Serial):
    r"""
    Mock pyserial Serial class that is capable of mocking serial commands a responses to
    for both simple and sophisticated neeeds. Breakfast Cereal allows you to defined
    simple :class:`~granola.command_readersCannedQueries` that are are predefined
    serial commands and responses for various commands. As well as more complicated
    :class:`~granola.command_readers.GettersAndSetters` which allow on the fly changing
    the state of stored attributes. It also allows customizing the behavior of how
    individual or any set of commands are processed through :mod:`~granola.hooks.hooks`.

    Mock serials initialization follows a 2 step process. The first is with the normal ``__init__``
    method where you pass arguments to Cereal, you can do this before your project is going,
    as part of the setup. At this point, Cereal will be able to mock but it won't have many
    pyserial Serial attributes defined such as port, baudrate. Cereal is
    then able to be "initialized" a second time, following the signature of pyserial Serial class.
    This allows you to setup Cereal with its configuration before and then not have to
    change your code that initializes Pyserial much or at all through means of depencency injection
    or patching.

    The CSVs must have the columns cmd and response in them, it can have other columns as well.

    Args:
        command_readers (dict[BaseCommandReaders|str] | list[BaseCommandReaders|str], optional):
            Dictionary or list of :mod:`Command Readers <granola.command_readers>`. Command Readers
            can be passed in as a string representation, or you may pass in the class itself.
            Passing in a dictionary allows specifying your initialization options as well.
            Using a list allows you to pass in already initialized Command Reader, or a not
            initialized Command Reader that will be initialized to default values.
            You can pass in custom Command Readers as well. See
            :ref:`Command Readers and Hooks Configuration`.
            defaults to ``(GettersAndSetters(), CannedQueries())``

        hooks (dict[BaseHook|str] | list[BaseHook|str], optional):
            Dictionary or list of :mod:`Hooks <granola.hooks.hook>`. Hooks
            can be passed in as a string representation, or you may pass in the class itself.
            Passing in a dictionary allows specifying your initialization options as well.
            Using a list allows you to pass in already initialized Hook, or a not
            initialized Hook that will be initialized to default values.
            You can pass in custom Hooks as well. See
            :ref:`Command Readers and Hooks Configuration`.
            defaults to ``[]``

        data_path_root (str | Path, optional): Path to the where all data file paths (for
            Command Readers or Custom Hooks) will be referenced from.

            .. todo::

                probably just make this a thing inside the needed command readers

        unsupported_response(str, optional):
            The response returned for any command that does not have a defined response.
            Defaults to "Unsupported\r>"

        encoding(str, optional): The encoding scheme used to encode the serial commands and responses
            Defaults to "ascii"

        .. todo::

            Allow passing in write terminator

    See Also
    --------
    :meth:`granola.breakfast_cereal.Cereal.mock_from_json` : Constructor from external configuration file.

    :ref:`Configuration Overview` : Configuration Instructions

    :ref:`Basic Overview of Mock Cereal and API` : Intro Tutorial
    """

    @add_created_at
    def __init__(
        self,
        command_readers=None,
        hooks=None,
        data_path_root=None,
        unsupported_response="Unsupported\r>",
        encoding="ascii",
    ):
        self._data_path_root = (
            data_path_root if data_path_root is not None else os.path.join(os.getcwd(), "config.json")
        )
        hooks = hooks if hooks is not None else []
        command_readers = command_readers if command_readers is not None else []

        self._unsupported_response = unsupported_response
        self._encoding = encoding
        self._write_terminator = "\r"  # TODO madeline, make this something to pass in from config.

        self._readers_ = self._setup_command_readers_and_hooks(command_readers, hooks)

        self._hooks_ = []
        self._next_read = ""  # The next read for this "serial" device
        self._next_write = ""  # The current write buffer to the serial device

        if check_min_package_version("pyserial", "3.0"):  # mocking pyserial is_open/_isOpen for different pyserials
            self.is_open = True
        else:
            self._isOpen = True

    @classmethod
    def mock_from_json(cls, config_key, config_path="config.json", *args, **kwargs):
        """
        Load configuration dictionary based on config_key and config_path and return a
        Breakfast Cereal class.

        If you don't pass in where config_path is, it will default to "config.json" in the
            root directory of your python path.
        """
        config = cls._load_json_config(config_key=config_key, config_path=config_path)
        kwargs.update(config)
        return cls(data_path_root=config_path, *args, **kwargs)

    @classmethod
    def _load_json_config(cls, config_key, config_path="config.json"):
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
        """
        Method to initialize pyserial Serial object. Serperating out the initialization of
        Breakfast Cereal into its own ``__init__`` method and then initializing pyserial in its
        __call__ method allows you to setup up Breakfast Cereal configuration outside of your
        code, and then have your code initialize it again to initialize the pyserial part of
        Breakfast Cereal. That way you can modify your own code as minimally as possible.

        Args:
            args: args to pass to pyserial
            kwargs: keyword arguments to pass to pyserial

        Raises:
            TypeError if you use __call__ more than once (and therefore pyserial is already
            initialized).
        """
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

                for reader in self._readers_.values():
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

    def _setup_command_readers_and_hooks(self, command_readers, hooks):
        readers = OrderedDict()
        config_command_readers = self._read_file_config_command_readers(command_readers)
        if config_command_readers:
            for reader in config_command_readers:
                readers[reader.__class__.__name__] = reader
        else:
            command_readers = (GettersAndSetters, CannedQueries)
            for reader in command_readers:
                cr = reader()
                readers[cr.__class__.__name__] = cr

        config_hooks = self._read_file_config_hooks(hooks)
        if config_hooks:
            hooks = config_hooks
        for hook in hooks:
            if inspect.isclass(hook):  # initialize uninitialized hook to their default args
                hook = hook()
            for cls in hook.hooked_classes:
                readers[cls.__name__].register_hook(hook)

        for reader in readers.values():
            reader.assign_default_hook()

        return readers

    def _read_file_config_from_classes(baseclass):
        """
        closure to generate functions that will match passed in configuration option classes
        to a subclass of ``baseclass``. This allows users to pass in classes they want to use
        for things like Hooks, CommandReaders or other things inside a configuration dictionary (JSON).

        Args:
            baseclass (class): Class to check all subclasses of when you know class from config_options
        """

        def _inner(self, config_options):
            subclasses = _get_subclasses(baseclass)
            classes = []
            if isinstance(config_options, list):
                for cls in config_options:
                    if isinstance(cls, str):
                        c = subclasses[cls]()
                    elif inspect.isclass(cls):  # initialize uninitialized class
                        c = cls()
                    else:
                        c = cls
                    classes.append(c)
            else:
                for cls, options in config_options.items():
                    # add config path, but will be overwritten if defined in options
                    opts = {"data_path_root": self._data_path_root}
                    opts.update(options)
                    if isinstance(cls, str):
                        c = subclasses[cls](**opts)
                    elif inspect.isclass(cls):  # initialize uninitialized class
                        c = cls(**opts)
                    else:
                        c = cls
                    classes.append(c)
            return classes

        return _inner

    _read_file_config_hooks = _read_file_config_from_classes(BaseHook)

    _read_file_config_command_readers = _read_file_config_from_classes(BaseCommandReaders)
