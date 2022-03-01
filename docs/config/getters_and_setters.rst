=================================
Getters and Setters Configuration
=================================

.. todo::
    Allow different eol characters

To use the :mod:`Command Reader <granola.command_readers>` :class:`~granola.command_readers.GettersAndSetters`, you must define
``"getters_and_setters"`` as a dictionary in your configuration.


********************
Dictionary Sections
********************

The different sections inside this dictionary are

"default_values"
------------------


The default values for the attributes that you will be storing, that is, the values they will be initially set to if you call a
getter before you call a setter.

"getters"
------------------


The getter serial commands and their responses. The getter commands are specified as a string with your eol characters,
and the response is a string with :std:doc:`Jinja2 <intro>` variable formatting.

This allows you to do basic equations inside the response, such as combining multiple attributes,
doing unit conversion, and other things.

"setters"
------------------

The setter serial commands and their responses. The setter commands change the stored attributes you initially set up
inside ``"default_values"``. Both the commands and responses uses :std:doc:`Jinja2 <intro>`
variable formatting.

.. caution::

    The jinja2 formatting inside the cmd field for setters currently can only accept the name of an attribute

Example
------------------

.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "getters_and_setters": {"default_values": {"sn": "42",
    ...                                                "temp": "20.0",
    ...                                                "conversion_factor": "7.0"},
    ...                             "getters": [{"cmd": "get -sn\r",
    ...                                          "response": "{{ sn }}\r>"},
    ...                                         {"cmd": "get -temp\r",
    ...                                          "response": "{{ temp }}\r>"},
    ...                                         {"cmd": "get -tempf\r",
    ...                                          "response": "{{ temp|float * (9/5) + 32 }}\r>"},
    ...                                         {"cmd": "get temp_convt\r",
    ...                                          "response": "{{ (temp|float + conversion_factor|float) / 2 }}"}],
    ...                             "setters": [{"cmd": "set -sn {{sn}}\r",
    ...                                          "response": "OK\r>"},
    ...                                         {"cmd": "set sn and temp {{ sn }} {{ temp }}\r",
    ...                                          "response": "serial number {{ sn }} temp: {{temp}}"},
    ...                                         {"cmd": "set -temp {{ temp }}\r",
    ...                                          "response": "{{ temp }}"},
    ...                                         {"cmd": "set convt {{ conversion_factor }}\r",
    ...                                          "response": "Conversion Factor {{ conversion_factor }}"}]}
    ... }
    >>> cereal = granola.Cereal(config)
    >>> cereal.write(b"get -sn\r")
    8
    >>> cereal.read(10)
    b'42\r>'
    >>> cereal.write(b"set -sn granola42\r")
    18
    >>> cereal.read(10)
    b'OK\r>'
    >>> cereal.write(b"get -sn\r")
    8
    >>> cereal.read(10)
    b'granola42\r'
    >>> cereal.write(b"get -tempf\r")
    11
    >>> cereal.read(10)
    b'68.0\r>'

Customizing Jinja
------------------

If the default jinja2 templating characters are incompatible with your serial commands, you can configure those
in your configuration dictionary as so.

.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "getters_and_setters": {"default_values": {"sn": "42"},
    ...                             "getters": [{"cmd": "get -sn\r",
    ...                                          "response": "`sn`\r>"}],
    ...                             "setters": [{"cmd": "set -sn `sn`\r",
    ...                                          "response": "OK\r>"}],
    ...                             "variable_start_string": "`",
    ...                             "variable_end_string": "`"
    ...                             }
    ... }
    >>>
    >>> cereal = granola.Cereal(config)
    >>> cereal.write(b"set -sn granola42\r")
    18
    >>> cereal.read(10)
    b'OK\r>'
    >>> cereal.write(b"get -sn\r")
    8
    >>> cereal.read(10)
    b'granola42\r'