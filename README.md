# GRANOLA


GRANOLA (Generating Real-time Autonomous N-device Output without Linked Apparatuses) is a package aiming to mock [Pyserial](https://pyserial.readthedocs.io/en/latest/)'s Serial
class with the goal of enabling automated testing, faster QA, and faster delivery. The core of this package is the class
Cereal. Cereal allows you to define complicated command and response sequences, getters and setters for commands that set attributes
on your device (such as the serial number), a hook system to inject your own needed functionality, and a Serial Sniffer to capture serial
command output from a real device as the basis of mocking later.

> :warning: ** This project is still in it's beta, pre 1.0 stage, and we are moving towards our 1.0 release. We try and not break previous interfaces when we move to new, but until it is ready for 1.0, it is still unstable.**

## Package Installation

To install:

``pip install granola``

## A Simple Example

``` python
>>> from granola import Cereal

>>> config = {"command_readers":{"CannedQueries": {"data": [{"1\r": "1", "2\r": ["2a", "2b"]}]}}}
... mock_cereal = Cereal(config)

>>> mock_cereal.write(b"2\r")
2
>>> mock_cereal.read(2)
b'2a'
>>> mock_cereal.write(b"1\r")
2
>>> mock_cereal.read(1)
b'1'
```

## Links

- Documentation: https://granola.readthedocs.io/en/stable/
- Examples: https://granola.readthedocs.io/en/stable/examples/examples_notebooks.html
- PyPI: https://pypi.org/project/granola/
- Source Code: https://github.com/metergroup/GRANOLA
- Issue Tracker: https://github.com/metergroup/GRANOLA/issues
