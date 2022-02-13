import pytest

from granola.tests.conftest import query_device


def test_bk_cereal_should_not_have_methods_that_arent_in_pyserial(mock_cereal):
    # Given a mock pyserial class has been initialized

    with pytest.raises(AttributeError):
        # When we access a method implemented in not implemented  in pyserial and not in bk_cereal
        mock_cereal.some_random_method_name_that_doesnt_exist()
        # Then it should raise an error


def test_bk_cereal_should_default_to_configjson_in_same_directory_as_class_definition(mock_cereal):
    # Given a mock pyserial class has been defined in a directory with a config.json and not told about it

    # When we try and access anything from that mock serial
    query_device(mock_cereal, "get name")

    # It should be fine, and nothing should error out


def test_bk_cereal_should_raise_if_writing_with_unicode_strings(mock_cereal):
    # Given a mock pyserial class has been initialized and a unicode input
    input = u"get name\r"

    # When we write to the mock serial with this unicode string
    with pytest.raises(TypeError):
        mock_cereal.write(input)
        # Then it should raise a TypeError
