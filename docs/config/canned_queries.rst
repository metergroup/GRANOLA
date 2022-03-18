=================================
Canned Queries Configuration
=================================
..
    >>> import sys, pytest
    >>> is_python_35 = sys.version_info[0] == 3 and sys.version_info[1] == 5
    >>> if is_python_35:
    ...     pytest.skip("This doctest doesn't work with Python 3.5 because dictionary ordering is not guaranteed."
    ...                 " All of the behavior is the same, just the underlying pandas DataFrame order will be different")

To use the :mod:`Command Reader <granola.command_readers>` :class:`~granola.command_readers.CannedQueries`,
you must define ``"canned_queries"`` as a dictionary in your configuration.
Which involves having a ``"data"`` dictionary with either file paths listed or serial commands directly defined.

File Path Option
******************

>>> from granola import CannedQueries, Cereal

To define your serial commands with file paths given a cereal_cmds.csv like this::

    cmd,response
    start\r, OK\r>
    get -volt\r, 7800\r>
    get -volt\r, 8000\r>
    get -volt\r, 4000\r>
    check -integrity\r, GOOD\r>
    radio on\r, OK\r>
    get name\r, Cereal Test Fixture\r
    reset\r, OK\r>
    get batt\r, 100\r>

>>> command_readers = {"CannedQueries": {"data": ["cereal_cmds.csv"]}}
>>> cereal = Cereal(command_readers=command_readers)
>>> cereal._readers_["CannedQueries"].serial_df
                    cmd               response
0             start\r                  OK\r>
1         get -volt\r                7800\r>
2         get -volt\r                8000\r>
3         get -volt\r                4000\r>
4  check -integrity\r                GOOD\r>
5          radio on\r                  OK\r>
6          get name\r  Cereal Test Fixture\r
7             reset\r                  OK\r>
8          get batt\r                 100\r>


Each data file can also be defined either as an absolute path or as a relative path path.
If you define your paths as a relative path, they are defined in relation to :class:`.Cereal`'s input parameter
``data_path_root``. See :class:`.Cereal` for more details.

Direct Serial Commands Option
*****************************

You can pass either a single value to be broadcasted to every value in a DataFrame,
or make a list of values that must be the same length as the DataFrames it is matching
against.

The specific formats you must follow can be seen with the :py:class:`~granola.command_readers.CannedQueries` Command Reader.
This is a quick overview of all the options for inside the serial commands dictionary.

>>> command_readers = {
...     "CannedQueries": {
...         "data": [
...             {
...                 "cmd1\r": "some response\r>",
...                 "cmd2\r": {"response": "some response\r"},
...                 "cmd3\r": {"response": "some response\r>", "another_column": 1},
...                 "cmd4\r": {"response": ["some response1\r>", "some response2\r>"]},
...                 "cmd5\r": {"response": ["some response1\r>", "some response2\r>"], "another_column": 1},
...                 "cmd6\r": {"response": ["some response1\r>", "some response2\r>"], "another_column": [1, 2]},
...                 "cmd7\r": {"response": [["some response1\r>", {"another_column": 42}], "some response2\r>"]},
...                 "cmd8\r": {
...                     "response": [["some response1\r>", {"another_column": 42}], "some response2\r>"],
...                     "another_column": 1,
...                 },
...                 "cmd9\r": [["some response1\r>", {"another_column": 42}], "some response2\r>"],
...             }
...         ]
...     },
... }
>>> cereal = Cereal(command_readers=command_readers)
>>> cereal._readers_["CannedQueries"].serial_df
       cmd           response  another_column
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
14  cmd9\r  some response2\r>             NaN

This can be expressed either in the JSON configuration or directly in python. Let's step through those options.
Generate a `SerialCmds` from a dictionary of serial commands. Here is the most basic form, where each command is mapped directly to a single response.

>>> command_readers = {
...     "CannedQueries": {"data": [{"test -off\r": "OK\r>", "get -sn\r": "1234|r>"}]
... }}
>>> cereal = Cereal(command_readers=command_readers)
>>> cereal._readers_["CannedQueries"].serial_df
           cmd response
0  test -off\r    OK\r>
1    get -sn\r  1234|r>

Here we can map multiple responses to ``get -temp\r``. They are ordered as well.
Just as any normal python list is ordered (20\r comes before 22\r).

Notice also that we also can map just a single response to ``test -off\r`` with this more verbose form

>>> command_readers = {
...     "CannedQueries": {"data": [{"get -temp\r": {"response": ["20\r>", "22\r>"]},
...                                 "test -off\r": {"response": "OK\r>"}}]}}
>>> cereal = Cereal(command_readers=command_readers)
>>> cereal._readers_["CannedQueries"].serial_df
           cmd response
0  get -temp\r    20\r>
1  get -temp\r    22\r>
2  test -off\r    OK\r>

Here we look at how to pass additional columns to our constructed DataFrame

>>> command_readers = {
...     "CannedQueries": {
...         "data": [{"get -temp\r": {"response": ["20\r>", "22\r>"]}, "test -volt\r": ["5000\r>", "6000\r>"]}],
...         "delay": 2,
...         "other_column": [1, 2, 3, 4]
...     },
... }
>>> cereal = Cereal(command_readers=command_readers)
>>> cereal._readers_["CannedQueries"].serial_df.sort_values(by="cmd")
            cmd response  delay  other_column
0   get -temp\r    20\r>      2             1
1   get -temp\r    22\r>      2             2
2  test -volt\r  5000\r>      2             3
3  test -volt\r  6000\r>      2             4

This last example showcases that we can broadcast delay=2 to the whole DataFrame since if
it is a single value, or we can supply as many values as serial rows (In the list for ``"other_column"``,
if we pass 2, 3, or more than 4 values, then it wouldn't have been clear which value went to which
response, so it does not allow that.)

We can also pass multiple response directly as a list, without having to embed it in a
dictionary.

Finally, we will look at 2 ways to specify extra fields on individual rows. We also look how we can pass
CannedQueries as the actual class instead of a string

>>> command_readers = {
...     CannedQueries: {
...         "data": [
...             {
...                 "get -temp\r": {
...                     "response": ["20\r>", "22\r>"],
...                     "delay": [7, 6],
...                 },
...                 "test -volt\r": {"response": ["5000\r>", ["6000\r>", {"delay": 5}], "5000\r>"], "delay": 4},
...                 "test -off\r": {"response": "OK\r>", "delay": 3},
...                 "get -sn\r": "1234|r>",
...             }
...         ],
...     },
... }
>>> cereal = Cereal(command_readers=command_readers)
>>> cereal._readers_["CannedQueries"].serial_df.sort_values(by="cmd")
            cmd response  delay
6     get -sn\r  1234|r>    NaN
0   get -temp\r    20\r>    7.0
1   get -temp\r    22\r>    6.0
5   test -off\r    OK\r>    3.0
2  test -volt\r  5000\r>    4.0
3  test -volt\r  6000\r>    5.0
4  test -volt\r  5000\r>    4.0
