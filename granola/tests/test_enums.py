import pytest
from granola.enums import SetRelationship, get_attribute_from_enum, validate_enum


def test_get_attribute_from_enum_should_return_the_passed_in_enum_value():
    # Given an enum and an attribue we want
    enum = SetRelationship.include
    attribue = "name"

    # When we get that attribute with get_attribute_from_enum
    name = get_attribute_from_enum(enum, attribue)

    # Then it is the name of that attribute
    true_name = "include"
    assert true_name == name


def test_get_attribute_from_enum_should_a_str_when_passed_a_str():
    # Given an string
    string = "some string"
    attribue = "name"

    # When we call get_attribute_from_enum with the string
    name = get_attribute_from_enum(string, attribue)

    # Then we get back the string we passed in
    assert string == name


def test_validate_enum_should_validate_a_correct_enum_type_value():
    # Given an enum and one of its values as an enum type
    enum = SetRelationship
    value = SetRelationship.include

    # When we validate that the enum is in fact of that enum type
    validate_enum(value, enum)

    # Then no errors should be raised


def test_validate_enum_should_validate_an_correct_str_type_value():
    # Given an enum and one of its values as an string
    enum = SetRelationship
    value = "include"

    # When we validate that the enum is in fact of that enum type
    validate_enum(value, enum)

    # Then no errors should be raised


def test_validate_enum_should_raise_an_ValueError_on_incorrect_value():
    # Given an enum and an incorrect value
    enum = SetRelationship
    value = "Some incorrect value"

    # When we validate that the enum is in fact of that enum type
    with pytest.raises(ValueError):
        validate_enum(value, enum)
        # Then it should raise a ValueError
