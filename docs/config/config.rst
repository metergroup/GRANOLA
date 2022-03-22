########################
Configuration Overview
########################

.. toctree::
    :maxdepth: 1
    :caption: In-depth Guides

    Canned Queries <canned_queries>
    Getters and Setters <getters_and_setters>
    Custom Command Readers and Hooks <cr_hooks_cfg>

.. toctree::
    :maxdepth: 2
    :caption: Examples

    ../examples/examples_notebooks

**************************
What is a Command Reader?
**************************

:mod:`Command Readers <granola.command_readers>` are the objects that handle the processing of individual serial
commands. Each serial command that comes in is processed by each :mod:`Command Reader <granola.command_readers>`, and
once a :mod:`Command Reader <granola.command_readers>` returns a valid response, the next
:mod:`Command Readers <granola.command_readers>` will skip processing the command. This allows you to change the
behavior of individual commands by defining new :mod:`Command Readers <granola.command_readers>`.

Canned Queries
==============

The most basic :mod:`Command Reader <granola.command_readers>` is the :class:`~granola.command_readers.CannedQueries` Command Reader.
This Command Reader has you define a series of commands and a responses, and then when a command comes in, it with return
the next matching response for that command. It will iterate through the subset of matching commands (ex: all "get sn\r"),
until it reaches the end. There are ways with :ref:`Hooks <What is a Hook?>` to define the behavior of what happens when it
reaches the end.

You can see a more in-depth tutorial on :class:`~granola.command_readers.CannedQueries` :ref:`here <Canned Queries Configuration>`.

Getters And Setters
===================

Another useful :mod:`Command Reader <granola.command_readers>` is the :class:`~granola.command_readers.GettersAndSetters` Command Reader.
This Command Reader manages the state of a number of attributes which you can access with getters and set with setters.
It initializes some default values and stores those values in the attribute. These attributes can then be modified with
setters, and then grabbed from the getters. Both getters and setters allow configuration with using :std:doc:`Jinja2 <jinja2:intro>` formatting.

You can see a more in-depth tutorial on :class:`~granola.command_readers.GettersAndSetters` :ref:`here <Getters and Setters Configuration>`.



****************
What is a Hook?
****************

A :mod:`Hook <granola.hooks.hooks>` is class that is associated with a :mod:`Command Reader <granola.command_readers>` or set of Command Readers and runs extra code at predefined
location. Before each :mod:`Command Readers's <granola.command_readers>` :meth:`~granola.command_readers.BaseCommandReaders.get_reading`
method, a Hook can be ran, via :meth:`~granola.hook.base_hook.BaseHook.pre_reading`, processing the incoming data,
saving information about it for later, modifying it, or any other useful actions. Alternatively, a Hook can run after
:meth:`~granola.command_readers.BaseCommandReaders.get_reading`, via :meth:`~granola.hook.base_hook.BaseHook.post_reading`,
altering the resulting response, using information from prior state, or other more sophisticated techniques.

For information on creating your own hooks, see :mod:`~granola.hooks.base_hook`


****************************************
Moving to 0.9.0 from a previous release
****************************************

.. toctree::

    moving_to_v0_9_0