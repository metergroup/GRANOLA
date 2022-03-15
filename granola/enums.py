from granola.utils import IS_PYTHON3

if IS_PYTHON3:
    from enum import Enum
else:  # pragma: no cover
    from aenum import Enum


def get_attribute_from_enum(maybe_enum, enum_attribute):
    """If the passed in maybe_enum is an enum, return the attribute, else return the maybe_enum

    Args:
        maybe_enum (Enum or Enum key)
        enum_attribute (str): The name of the enum attribute to retrieve
    """
    if isinstance(maybe_enum, Enum):
        return getattr(maybe_enum, enum_attribute)
    return maybe_enum


def validate_enum(value, enum):
    """Validate the given value is in the given enum

    Args:
        value (Enum or enum key)
        enum: the enum to validate against
    """
    error = ValueError("Invalid Enum Option\nEnum -- %s\nOption supplied -- %s" % (enum.str_enum_options(), value))
    if isinstance(value, Enum):
        if value not in enum:
            raise error
    elif value not in enum.__members__:
        raise error


class DocumentedEnum(Enum):
    def __init__(self, description):
        self.description = description

    @classmethod
    def str_enum_options(cls):
        string = "{enum}\n".format(enum=cls.__name__)
        nl = "\n"
        string += nl.join(
            "Option: {name} -- Description: {doc}".format(name=enum.name, doc=enum.description) for enum in cls
        )
        return string


class RandomizeResponse(DocumentedEnum):
    """
    The different ways to specify to randomize or not randomize your
    :class:`~granola.command_readers.CannedQueries` response
    """

    not_randomized = "Don't randomize the response"
    randomized_w_replacement = "Randomize with replacement"
    randomize_and_remove = "Randomize and remove"


class HookTypes(DocumentedEnum):
    """
    Allowed hook types for ``BaseHook`` methods or for a ``register_hook``
    Current allowed hook types are ``pre_reading`` and ``post_reading``.
    """

    pre_reading = "Hook to run before `get_reading` methods"
    post_reading = "Hook to run after `get_reading` methods"


class SetRelationship(DocumentedEnum):
    """
    The different ways to specify what a hook should do with commands or attributes,
    should the hook ``include`` everything listed in the corresponding data container
    and nothing else, or should it exclude everything in the corresponding data container
    and include everything else.
    """

    include = "Include everything listed in the corresponding data container"
    exclude = "Exclude everything listed in the corresponding data container"
