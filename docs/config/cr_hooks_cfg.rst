=========================================
Command Readers and Hooks Configuration
=========================================


***********************
Custom Command Readers
***********************

To pass custom :mod:`Command Readers <granola.command_readers>`, as well as to change the
order they are processed in, you can define ``"command_readers"`` in your configuration.

That would look like this


>>> from granola import BaseCommandReaders, Cereal, register_hook, CannedQueries

>>> class CommandReader(BaseCommandReaders):
...     def get_reading(self, data):
...         return "Command Reader"

>>> command_readers = [CommandReader]
>>> cereal = Cereal(command_readers=command_readers)
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


>>> @register_hook(hook_type_enum="post_reading", hooked_classes=[CannedQueries])
... def hook(self, hooked, result, data, **kwargs):
...     return "1"

>>> command_readers = {"CannedQueries": {"data": [{"cmd\r": "response"}]}}
>>> hooks = [hook]
>>> cereal = Cereal(command_readers=command_readers, hooks=hooks)
>>> cereal.write(b"cmd\r")
4
>>> cereal.read(cereal.in_waiting)
b'1'

You can either specify the Hook directly, or the name of it as a string. If you specify
it as a string, then the Hook needs to be imported or defined before you initialize :class:`~granola.breakfast_cereal.Cereal`

You can also pass addition arguments to a hook like this.

>>> command_readers = {"CannedQueries": {"data": [{"cmd\r": ["1", "2"]}]}}
>>> hooks = {"StickCannedQueries": {"attributes": ["cmd\r"], "include_or_exclude": "include"}}
>>> cereal = Cereal(command_readers=command_readers, hooks=hooks)
>>> cereal.write(b"cmd\r")
4
>>> cereal.read(cereal.in_waiting)
b'1'
>>> cereal.write(b"cmd\r")
4
>>> cereal.read(cereal.in_waiting)
b'2'
>>> cereal.write(b"cmd\r")
4
>>> cereal.read(cereal.in_waiting)
b'2'
