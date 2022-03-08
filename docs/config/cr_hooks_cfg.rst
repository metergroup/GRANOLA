=========================================
Command Readers and Hooks Configuration
=========================================

**************************
What is a Command Reader?
**************************

:mod:`Command Readers <granola.command_readers>` are the objects that handle the processing of individual serial
commands. Each serial command that comes in is processed by each :mod:`Command Reader <granola.command_readers>`, and
once a :mod:`Command Reader <granola.command_readers>` returns a response, the next
:mod:`Command Readers <granola.command_readers>` will skip processing the command. This allows you to change the
behavior of individual commands by defining new :mod:`Command Readers <granola.command_readers>`. The most basic
:mod:`Command Reader <granola.command_readers>` is the :class:`~granola.command_readers.CannedQueries` Command Reader.
This Command Reader has you define a series of commands and a responses, and then when a command comes in, it with return
the next matching response for that command. It will iterate through the subset of catching commands (so all "get sn\r"),
until it reaches the end. There are ways with hooks (the next section) to define the behavior of what happens when it
reaches the end. You can see an overview of the configuration options for

Another useful :mod:`Command Reader <granola.command_readers>` is the :class:`~granola.command_readers.GettersAndSetters`


 You can configure configure new types of behavior for different,


Already available :mod:`Hooks <granola.hooks.hooks>` and :mod:`Command Readers <granola.command_readers>` are available, but

***********************
Custom Command Readers
***********************

To pass custom :mod:`Command Readers <granola.command_readers>`, as well as to change the
order they are processed in, you can define ``"command_readers"`` in your configuration.

That would look like this


.. doctest::
    :pyversion: >= 3.6

    >>> class CommandReader(granola.BaseCommandReaders):
    ...     def get_reading(self, data):
    ...         return "Command Reader"

    >>> config = {"command_readers": [CommandReader]}
    >>> cereal = granola.Cereal(config)
    >>> cereal.write(b"\r")
    1
    >>> cereal.read(20)
    b'Command Reader'

You can either specify the CommandReader directly, or the name of it as a string. If you specify
it as a string, then the CommandReader needs to be imported or defined before you initialize :class:`~granola.breakfast_cereal.Cereal`

****************
Custom Hooks
****************



To pass custom :mod:`~granola.hooks.hooks`, as well as to change the
order they are processed in, you can define ``"hooks"`` in your configuration.

That would look like this


.. doctest::
    :pyversion: >= 3.6

    >>> @granola.register_hook(hook_type_enum=granola.HookTypes.post_reading, hooked_classes=[granola.CannedQueries])
    ... def hook(self, hooked, result, data, **kwargs):
    ...     return "1"

    >>> config = {
    ...     "canned_queries": {
    ...         "data": {
    ...             "`DEFAULT`": {"cmd\r": "response"}
    ...         }
    ...     },
    ...     "hooks": ["hook"]
    ... }

    >>> cereal = granola.Cereal(config)
    >>> cereal.write(b"cmd\r")
    4
    >>> cereal.read(5)
    b'1'

You can either specify the Hook directly, or the name of it as a string. If you specify
it as a string, then the Hook needs to be imported or defined before you initialize :class:`~granola.breakfast_cereal.Cereal`

You can also pass addition arguments to a hook like this.


.. doctest::
    :pyversion: >= 3.6

    >>> config = {
    ...     "canned_queries": {
    ...         "data": {
    ...             "`DEFAULT`": {"cmd\r": ["1", "2"]}
    ...         }
    ...     },
    ...     "hooks": [
    ...         {"hook_type": "StickCannedQueries",
    ...          "attributes": ["cmd\r"],
    ...          "include_or_exclude": "include"}
    ...     ]
    ... }
    >>> cereal = granola.Cereal(config)
    >>> cereal.write(b"cmd\r")
    4
    >>> cereal.read(5)
    b'1'
    >>> cereal.write(b"cmd\r")
    4
    >>> cereal.read(5)
    b'2'
    >>> cereal.write(b"cmd\r")
    4
    >>> cereal.read(5)
    b'2'
