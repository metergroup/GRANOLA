#########################################
Moving to 0.9.0 From a Previous Release
#########################################

See Also:
- :ref:`Configuration Overview`
- :ref:`Canned Queries Configuration`
- :ref:`Getters and Setters Configuration`
- :ref:`Custom Command Readers and Hooks Configuration`
- :std:doc:`Jinja2 <jinja2:intro>`

To move from a previous release to 0.9.0, the main differences will be that you
will want to move to :class:`.Cereal` from :class:`.MockSerial`.

*************************
Configuration from JSON
*************************

The next big thing will be to update your configuration. If you configure from a json file, you
will want to use ``Cereal.mock_from_json`` instead of directly instantiating ``Cereal``.

Let's walk through the configuration changes with an example.
If your old configuration looks something like this:

.. code-block::

    // config.json

    {
        "config_key": {
            "unsupported_response": "ERROR\r>",
            "canned_queries": { "files": {
                "_default_csv_": "data/cereal_cmds.csv",
                "sdicmd 1 get-measurement": "data\\sensor_get_reading_cmds.csv",
                "sdicmd 1": "data\\sensor_cmds.csv"
                }},
            "getters_and_setters": {
                "default_values": {
                    "sn": "42",
                },
                "getters": [
                    {
                        "getter": "get -sn\r",
                        "response": "`sn`\r>"
                    }
                ],
                "setters": [
                    {
                        "setter": "set -sn `sn`\r",
                        "response": "OK\r>"
                    }
                ]
            }
        }
    }

A newly formatted configuration would look like this:

.. code-block::

    // config.json

    {
        "config_key": {
            "unsupported_response": "ERROR\r>",
            "command_readers": {
                "CannedQueries": { "data": [
                    "data/cereal_cmds.csv",
                    "data\\sensor_get_reading_cmds.csv",
                    "data\\sensor_cmds.csv"
                ]
                },
                "GettersAndSetters": {
                    "default_values": {
                        "sn": "42",
                    },
                    "getters": [
                        {
                            "cmd": "get -sn\r",
                            "response": "{{ sn }}\r>"
                        }
                    ],
                    "setters": [
                        {
                            "cmd": "set -sn {{ sn }}\r",
                            "response": "OK\r>"
                        }
                    ]
                }
            }
        }
    }

Taking this apart, piece by piece, first,

.. code-block::

    {
        "config_key": {
            "canned_queries": ...
            "getters_and_setters": ...
        }
    }

The ``canned_queries`` configuration and ``getters_and_setters`` configuration have moved inside the ``command_readers``
section, with all options to pass to them, specified as keys and values of a dictionary (there are other ways to pass
Command Readers in, such as already initialized, but see the see also above for more information). We also noticed
that they have changed from ``canned_queries`` and ``getters_and_setters`` to ``CannedQueries`` and ``GettersAndSetters``.
This is because they now reference the actual Command Reader you are configuring, which are :class:`.CannedQueries` and
:class:`.GettersAndSetters`.

.. code-block::

    {
        "config_key": {
            "command_readers": {
                "CannedQueries": ...
                "GettersAndSetters": ...
            }
        }
    }

Next inside ``CannedQueries``, we see that the key ``files`` has changed to ``data``

.. code-block::

    {
        "config_key": {
            "command_readers": {
                "CannedQueries": "data": ...
            }
        }
    }

This is because you can now pass in serial commands :ref:`directly <Canned Queries Configuration>`,
instead of just as paths to csv files.


The use of ``_default_csv_`` has been removed, and now all files (or dictionaries of serial commands) are just defined
in a list, since it doesn't make functional changes and simplifies the codebase and configuration.

.. code-block::

    {
        "config_key": {
            "command_readers": {
                "CannedQueries": "data": [
                    file1, file2, etc
                ]
            }
        }
    }

In GettersAndSetters, instead of specifying your variable substitutions with backticks (\`). Now you specify them with
jinja2 formatting {{ }}.

.. code-block::

    {
        "config_key": {
            "unsupported_response": "ERROR\r>",
            "command_readers": {
                "GettersAndSetters": {
                    "default_values": {
                        "sn": "42",
                    },
                    "getters": [
                        {
                            "cmd": "get -sn\r",
                            "response": "{{ sn }}\r>"
                        }
                    ],
                    "setters": [
                        {
                            "cmd": "set -sn {{ sn }}\r",
                            "response": "OK\r>"
                        }
                    ]
                }
            }
        }
    }

If need be, you can specify what :std:doc:`Jinja2 <jinja2:intro>` start and end strings to use with the configuration options
`"variable_start_string"` and `"variable_end_string"` like so.

.. code-block::

    {
        "config_key": {
            "unsupported_response": "ERROR\r>",
            "command_readers": {
                "GettersAndSetters": {
                    "default_values": {
                        "sn": "42",
                    },
                    "getters": [
                        {
                            "cmd": "get -sn\r",
                            "response": "`sn`\r>"
                        }
                    ],
                    "setters": [
                        {
                            "cmd": "set -sn `sn`\r",
                            "response": "OK\r>"
                        }
                    ],
                    "variable_start_string": "`",
                    "variable_end_string": "`"
                }
            }
        }
    }

With the change to using :std:doc:`Jinja2 <jinja2:intro>` as our templating engine, it has opened up a lot more
and powerful options for customizing your serial command logic. Such as multiplying different attributes together.
See :ref:`Getters and Setters Configuration` for more information.

One final thing to note with the changes to using Cereal, all options can now be included with either the configuration
file, or directly instantiating, you no longer have to do a little of both. See the above links for more information
on configuration options.

*************************
Configuration in Code
*************************

Everything in the above section holds true, because the only difference between how you directly instantiate ``Cereal``
from how you instantiate it with ``Cereal.mock_from_json`` is that if you have a config like this


>>> config = {
...         "config_key": {
...             "unsupported_response": "ERROR\r>",
...             "command_readers": {
...                 "CannedQueries": { "data": [
...                     "cereal_cmds.csv"
...                 ]
...                 },
...                 "GettersAndSetters": {
...                     "default_values": {
...                         "sn": "42",
...                     },
...                     "getters": [
...                         {
...                             "cmd": "get -sn\r",
...                             "response": "{{ sn }}\r>"
...                         }
...                     ],
...                     "setters": [
...                         {
...                             "cmd": "set -sn {{ sn }}\r",
...                             "response": "OK\r>"
...                         }
...                     ]
...                 }
...             }
...         }
...     }

Which is the same as the new one from before, but now as a python dictionary.
Then your instantiation would be this

>>> from granola import Cereal
>>> cereal = Cereal(**config["config_key"])

That is to say, inside your configuration for a particular mock cereal (config["config_key"]), your keys are the
parameters of ``Cereal``

So you can do

>>> command_readers = {"CannedQueries": {"data": ["cereal_cmds.csv"]}}
>>> command_readers = {
...     "CannedQueries": {"data": ["cereal_cmds.csv"]},
...     "GettersAndSetters": {
...         "default_values": {"sn": "42", "temp": "20.0", "conversion_factor": "7.0"},
...         "getters": [
...             {"cmd": "get -sn\r", "response": "{{ sn }}\r>"},
...             {"cmd": "get -temp\r", "response": "{{ temp }}\r>"},
...             {"cmd": "get -tempf\r", "response": "{{ temp|float * (9/5) + 32 }}\r>"},
...             {"cmd": "get temp_convt\r", "response": "{{ (temp|float + conversion_factor|float) / 2 }}"},
...         ],
...         "setters": [
...             {"cmd": "set -sn {{sn}}\r", "response": "OK\r>"},
...             {"cmd": "set sn and temp {{ sn }} {{ temp }}\r", "response": "serial number {{ sn }} temp: {{temp}}"},
...             {"cmd": "set -temp {{ temp }}\r", "response": "{{ temp }}"},
...             {"cmd": "set convt {{ conversion_factor }}\r", "response": "Conversion Factor {{ conversion_factor }}"},
...         ],
...     }
... }
>>> unsupported_response = "ERROR\r>"
>>> hooks = {"StickCannedQueries": {"attributes": ["2\r"], "include_or_exclude": "include"}}
>>> cereal = Cereal(command_readers=command_readers, hooks=hooks, unsupported_response=unsupported_response)

And then continue everything else you normally do.