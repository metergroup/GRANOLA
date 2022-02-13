=================================
Canned Queries Configuration
=================================

To use the :mod:`Command Reader <granola.command_readers>` :class:`~granola.command_readers.CannedQueries`, you must define ``"canned_queries"`` as a dictionary in your configuration.
Which involves having a ``"data"`` dictionary with either file paths listed or serial commands directly defined.

File Path Option
******************

To define your serial commands with file paths

.. code-block:: JSON

    {
        "canned_queries": {
            "data": {
                "`DEFAULT`": "data\\fixture\\fixture_serial_cmds.csv",
                "sdicmd 1 \\?Xc!": "data\\sensor\\teros_12_get_reading_cmds.csv",
                "sdicmd 1": "data\\sensor\\teros_12_serial_cmds.csv"
            }
        }
    }

Where each key is a regex of a serial command you want to get routed to that csv. Searches
occur in order of top to bottom with the exception of ``"`DEFAULT`"``, which is
the csv that any command that doesn't have a matching key will search in.

Each file can also be defined either as a relative path to your configuration file (if you define your configuration
directly in python, and don't include the a ``config_path`` input, it defaults to the current working directory
for the relative base directory).

Direct Serial Command Definitions
************************************

To define your serial commands directly, here is a basic example

.. code-block:: JSON

    {
        "canned_queries": {
            "data": {
                "`DEFAULT`": {"get -temp\r": {"response": ["20\r>",
                                                            "22\r>"]},
                                "test -off\r": "OK\r>"}}
        }
    }

You can also additionally pass extra fields to to the resulting DataFrame, as such

.. code-block:: JSON

    {
        "canned_queries": {
            "data": {
                "`DEFAULT`": {"get -temp\r": {"response": ["20\r>",
                                                            "22\r>"]},
                                "test -off\r": "OK\r>"}},
            "extra_col1": 2
            "extra_col2": [1, 2, 3]
        }
    }

You can pass either a single value to be broadcasted to every value in a DataFrame,
or make a list of values that must be the same length as the DataFrames it is matching
against.

The specific formats you must follow can be seen with the :py:class:`~granola.command_readers.CannedQueries` Command Reader.
This is a quick overview of all the options for inside the serial commands dictionary.


.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "canned_queries": {
    ...         "data": {
    ...             "`DEFAULT`": {"cmd1\r": "some response\r>",
    ...                         "cmd2\r": {"response": "some response\r"},
    ...                         "cmd3\r": {"response": "some response\r>", "another_column": 1},
    ...                         "cmd4\r": {"response": ["some response1\r>",
    ...                                                 "some response2\r>"]},
    ...                         "cmd5\r": {"response": ["some response1\r>",
    ...                                                 "some response2\r>"],
    ...                                                 "another_column": 1},
    ...                         "cmd6\r": {"response": ["some response1\r>",
    ...                                                 "some response2\r>"],
    ...                                                 "another_column": [1,
    ...                                                                     2]},
    ...                         "cmd7\r": {"response": [["some response1\r>", {"another_column": 42}],
    ...                                                 "some response2\r>"]},
    ...                         "cmd8\r": {"response": [["some response1\r>", {"another_column": 42}],
    ...                                                 "some response2\r>"],
    ...                                                 "another_column": 1},
    ...                         "cmd9\r": [["some response1\r>", {"another_column": 42}],
    ...                                     "some response2\r>"]}
    ...         }
    ...     }
    ... }
    >>> canned_queries = granola.CannedQueries()
    >>> canned_queries.initialize_config(config)
    >>> canned_queries.serial_dfs
    OrderedDict([('`DEFAULT`',        cmd           response  another_column
    0   cmd1\r   some response\r>             NaN
    1   cmd2\r    some response\r             NaN
    2   cmd3\r   some response\r>             1.0
    3   cmd4\r  some response1\r>             NaN
    4   cmd4\r  some response2\r>             NaN
    5   cmd5\r  some response1\r>             1.0
    6   cmd5\r  some response2\r>             1.0
    7   cmd6\r  some response1\r>             1.0
    8   cmd6\r  some response2\r>             2.0
    9   cmd7\r  some response1\r>            42.0
    10  cmd7\r  some response2\r>             NaN
    11  cmd8\r  some response1\r>            42.0
    12  cmd8\r  some response2\r>             1.0
    13  cmd9\r  some response1\r>            42.0
    14  cmd9\r  some response2\r>             NaN)])

This can be expressed either in the JSON configuration or directly in python. Let's step through those options.
Generate a `SerialCmds` from a dictionary of serial commands. Here is the most basic form, where each command is mapped directly to a single response.

.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "canned_queries": {
    ...         "data": {
    ...             "`DEFAULT`": {"test -off\r": "OK\r>",
    ...                         "get -sn\r": "1234|r>"}
    ...         }
    ...     }
    ... }
    >>> canned_queries = granola.CannedQueries()
    >>> canned_queries.initialize_config(config)
    >>> canned_queries.serial_dfs
    OrderedDict([('`DEFAULT`',            cmd response
    0  test -off\r    OK\r>
    1    get -sn\r  1234|r>)])

Here we can map multiple responses to ``get -temp\r``. They are ordered as well.
Just as any normal python list is ordered (20\r comes before 22\r).

Notice also that we also can map just a single response to ``test -off\r`` with this more verbose form

.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "canned_queries": {
    ...         "data": {
    ...             "`DEFAULT`": {"get -temp\r": {"response": ["20\r>",
    ...                                                     "22\r>"]},
    ...                         "test -off\r": {"response": "OK\r>"}}
    ...         }
    ...     }
    ... }
    >>> canned_queries = granola.CannedQueries()
    >>> canned_queries.initialize_config(config)
    >>> canned_queries.serial_dfs
    OrderedDict([('`DEFAULT`',            cmd response
    0  get -temp\r    20\r>
    1  get -temp\r    22\r>
    2  test -off\r    OK\r>)])

Here we look at how to pass additional columns to our constructed DataFrame

.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "canned_queries": {
    ...         "data": {
    ...             "`DEFAULT`": {"get -temp\r": {"response": ["20\r>",
    ...                                                     "22\r>"]},
    ...                         "test -volt\r": ["5000\r>",
    ...                                         "6000\r>"]},
    ...         },
    ...         "delay": 2,
    ...         "other_column": [1, 2, 3, 4]
    ...     }
    ... }
    >>> canned_queries = granola.CannedQueries()
    >>> canned_queries.initialize_config(config)
    >>> canned_queries.serial_dfs
    OrderedDict([('`DEFAULT`',             cmd response  delay  other_column
    0   get -temp\r    20\r>      2             1
    1   get -temp\r    22\r>      2             2
    2  test -volt\r  5000\r>      2             3
    3  test -volt\r  6000\r>      2             4)])

This last example showcases that we can broadcast delay=2 to the whole DataFrame since if
it is a single value, or we can supply as many values as serial rows (In the list for ``"other_column"``,
if we pass 2, 3, or more than 4 values, then it wouldn't have been clear which value went to which
response, so it does not allow that.)

We can also pass multiple response directly as a list, without having to embed it in a
dictionary.

Finally, we will look at 2 ways to specify extra fields on individual rows.

.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "canned_queries": {
    ...         "data": {
    ...             "`DEFAULT`": {"get -temp\r": {"response": ["20\r>",
    ...                                                     "22\r>"],
    ...                                         "delay": [7,
    ...                                                     6],},
    ...                         "test -volt\r": {"response": ["5000\r>",
    ...                                                         ["6000\r>", {"delay": 5}],
    ...                                                         "5000\r>"],
    ...                                         "delay": 4},
    ...                         "test -off\r": {"response": "OK\r>", "delay": 3},
    ...                         "get -sn\r": "1234|r>"},
    ...         },
    ...     }
    ... }
    >>> canned_queries = granola.CannedQueries()
    >>> canned_queries.initialize_config(config)
    >>> canned_queries.serial_dfs
    OrderedDict([('`DEFAULT`',             cmd response  delay
    0   get -temp\r    20\r>    7.0
    1   get -temp\r    22\r>    6.0
    2  test -volt\r  5000\r>    4.0
    3  test -volt\r  6000\r>    5.0
    4  test -volt\r  5000\r>    4.0
    5   test -off\r    OK\r>    3.0
    6     get -sn\r  1234|r>    NaN)])