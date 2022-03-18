#######
GRANOLA
#######

GRANOLA (Generating Real-time Autonomous N-device Output without Linked Apparatuses) is a package aiming to mock :std:doc:`Pyserial's <pyserial:index>`
:class:`Serial <pyserial:serial.Serial>` class with the goal of enabling automated testing, faster QA, and faster delivery. The core of this package is the class
Cereal. Cereal allows you to define complicated command and response sequences, getters and setters for commands that set attributes
on your device (such as the serial number), a hook system to inject your own needed functionality, and a Serial Sniffer to capture serial
command output from a real device as the basis of mocking later.

****************
A Simple Example
****************

>>> from granola import Cereal
>>> command_readers = {"CannedQueries": {"data": [{"1\r": "1", "2\r": ["2a", "2b"]}]}}
>>> mock_cereal = Cereal(command_readers)

>>> mock_cereal.write(b"2\r")
2
>>> mock_cereal.read(10)
b'2a'
>>> mock_cereal.write(b"1\r")
2
>>> mock_cereal.read(10)
b'1'


.. warning::

    This project is still in it's beta, pre 1.0 stage with active development moving towards its 1.0 release.
    We try and not break previous interfaces when we move to new releases, but until it is ready for 1.0, it is still
    unstable.

.. toctree::
    :caption: Table of Contents
    :name: mastertoc
    :titlesonly:

    config/config
    API Overview <api>
    examples/examples_notebooks
    logging
