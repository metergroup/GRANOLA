# Welcome to GRANOLA's documentation!


GRANOLA (Generating Real-time Autonomous N-device Output without Linked Apparatuses) is a package aiming to mock pyserial's Serial
class with the goal of enabling automated testing, faster QA, and faster delivery. The core of this package is the class
Cereal. Cereal allows you to define complicated command and response sequences, getters and setters for commands that set attributes
on your device (such as the serial number), a hook system to inject your own needed functionality, and a Serial Sniffer to capture serial
command output from a real device as the basis of mocking later.

> :warning: ** This project is still in it's beta, pre 1.0 stage with active moving towards its 1.0 release. We try and not break previous interfaces when we move to new, but until it is ready for 1.0, it is still unstable.**

## Package Installation


To pull this package down in another project simply:

    TODO (madeline) update with pypi when available


## Read the Docs


TODO (madeline) fill in with link to readthedocs later


## A Simple Example

``` python
>>> from granola import Cereal

>>> config = {"command_readers":{"CannedQueries": {"data": [{"1\r": "1", "2\r": ["2a", "2b"]}]}}}
... mock_cereal = Cereal(config)

>>> mock_cereal.write(b"2\r")
2
>>> mock_cereal.read(10)
b'2a'
>>> mock_cereal.write(b"1\r")
2
>>> mock_cereal.read(10)
b'1'
```

### More Examples

TODO put link to examples docs stuff
