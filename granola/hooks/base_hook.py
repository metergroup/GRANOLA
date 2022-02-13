import functools
import inspect

from granola.enums import (
    HookTypes,
    SetRelationship,
    get_attribute_from_enum,
    validate_enum,
)
from granola.utils import ABC, IS_PYTHON3


class BaseHook(ABC):
    hooked_classes = []

    def __init__(self, attributes=None, include_or_exclude=SetRelationship.exclude, *args, **kwargs):
        self.attributes = attributes if attributes is not None else {}
        self.include_or_exclude = get_attribute_from_enum(maybe_enum=include_or_exclude, enum_attribute="name")
        validate_enum(self.include_or_exclude, SetRelationship)

    def pre_reading(self, hooked, data, **kwargs):
        """
        Run the pre_reading hook

        Args:
            hooked: instance of hooked class
            data (str): Serial command
        """

    def post_reading(self, hooked, result, data, **kwargs):
        """
        Run the post_reading hook

        Args:
            hooked: instance of hooked class
            result (str): Returned result from serial command.
            data (str): Serial command
        """


def register_hook(hook_type_enum, hooked_classes):  # TODO madeline allow passing in attributes and including
    """
    Register a function as a `BaseHook` subclass (this converts a function into a subclass of
    `BaseHook`. `hook_type` is the method(s) to insert your function as in the created subclass.
    (example, if you say `hook_types="pre_reading"`, then the decorated function will become the
    `pre_reading` method in the returned Hook class.

    Options for `hook_type` are any enum in `HookTypes`. `hooked_classes` are the classes that you
    wish to run this hook on.

    Args:
        hook_type (str | HookTypes): str representation of `HookTypes` or `HookTypes` instances themselves
            you wish to run this hook as. Your option(s) will be coverted to methods in the returned class.
        hooked_classes (list[BaseCommandReaders]): list of `BaseCommandReaders` that you wish to
            run this hook on.
    """
    hook_classes = hooked_classes

    def _register_hook(func):
        class RegisteredHook(BaseHook):
            hooked_classes = hook_classes

        hook_type = get_attribute_from_enum(hook_type_enum, "name")
        validate_enum(hook_type, HookTypes)
        if IS_PYTHON3:  # pragma: no cover
            inspection_getargspec = inspect.getfullargspec
        else:
            inspection_getargspec = inspect.getargspec
        func_args = inspection_getargspec(func).args  # grab function signature

        def hook(self, **kwargs):
            in_attribs = kwargs.get("data") in self.attributes
            include_attribs = self.include_or_exclude == SetRelationship.include.name
            exclude_attribs = self.include_or_exclude == SetRelationship.exclude.name
            # Only run if data is to be included or not excluded
            if (in_attribs and include_attribs) or (not in_attribs and exclude_attribs):

                # extract out the params of func from kwargs
                kws = {k: v for k, v in kwargs.items() if k in func_args}
                if "self" in func_args:
                    kws["self"] = self  # only pass in self if self in func signature
                return func(**kws)
            if "result" in kwargs:
                return kwargs["result"]

        # Copy over original function meta data to new class (in desired place, so functools doesn't work exactly)
        hook.__doc__ = func.__doc__
        RegisteredHook.__module__ = func.__module__
        RegisteredHook.__name__ = func.__name__

        setattr(RegisteredHook, hook_type, hook)

        return RegisteredHook

    return _register_hook


def _run_pre_reading_hooks(hooked, data, **kwargs):
    for hook in hooked._hooks:
        hook.pre_reading(hooked=hooked, data=data, **kwargs)


def _run_post_reading_hooks(hooked, result, data, **kwargs):
    for hook in hooked._hooks:
        result = hook.post_reading(hooked=hooked, result=result, data=data, **kwargs)
    return result


def wrap_in_hooks(func):
    """
    Decorator that wraps a function in hooks that will run pre and post function.

    wrapper args:
        hooked (CannedQueries): CannedQueries instance to run the hook on.
        result (str): Passed in result to potentially modify.
        data (str): Serial command.
    """

    @functools.wraps(func)
    def wrapper(hooked, data, **kwargs):
        _run_pre_reading_hooks(hooked=hooked, data=data, **kwargs)
        result = func(hooked, data, **kwargs)
        result = _run_post_reading_hooks(hooked=hooked, result=result, data=data, **kwargs)
        return result

    return wrapper


__doc__ = r"""
This module provides the abstract base class for Hook objects, ``BaseHook``.

``BaseHook`` outlines the framework to design a hook class.

* You inherit from ``BaseHook``
* specify your ``hooked_classes``, which is a list of all the classes that your hook will run on.
* If you need additional initialization arguments, you can override the default init, passing
  ``attributes`` and ``include_or_exclude`` to ``BaseHook`` init.
* Finally, define what hook methods you need. That might be running hooks ``pre_reading`` or
  ``post_reading`` or both

* You can also define a hook as a function instead of a class and then "register" it as a hook
  with the ``register_hook`` decorator below. This can be very efficient for simple hooks,
  but it does lose you the ability to run both a ``pre_reading`` and ``post_reading`` method
  on the same hook, which more complicated hooks maybe need.

****************
Hooks as Classes
****************

Here is an example of a hook class being created::

    .. code-block:: python

        from granola import GettersAndSetters, CannedQueries

        class MyHook(BaseHook):
            hooked_classes=[GettersAndSetters, CannedQueries]
            '''This is the list of classes that the hook will be run on.'''

            def __init__(self, attributes=["get -sn\r"], include_or_exclude="exclude", some_parameter="default_val"):
                '''attributes and include_or_exclude are parameters (with defaults) that come from
                BaseHook. This specifies which serial commands or other type of attribute will be
                include or exclude on your hook (which will be ran). By saying attributes=["get -sn\r"]
                and include_or_exclude="include" we are saying to exclude "get -sn\r" and
                include all other commands.
                '''

                super(MyHook, self).__init__(attributes=attributes, include_or_exclude=include_or_exclude)
                self.some_parameter = some_parameter
                self.calculated_value = None

            def pre_reading(self, hooked, data, **kwargs):
                '''store the length of the the incoming command (data) * ``self.some_parameter``
                self.calculated_value = self.some_parameter * len(data)

            def post_reading(self, hooked, result, data, **kwargs):
                '''Change the serial result to the previous ``self.calculated_value`` * ``len(result)``
                result = self.calculated_value * len(result)
                return result

Doing a hook this way, as a class definition allows you to specify a ``pre_reading`` and ``post_reading``
method on the same hook. Some hooks (such as the approach hook) rely on it being ran before and after the reading
to know the state before the actual reading, and to change the result for some commands.

******************
Hooks as Functions
******************

If your hook doesn't require both a ``pre_reading`` and ``post_reading``, you can instead just write
a function and decorate it with the :func:`~granola.hooks.base_hook.register_hook` decorator.

Here is an example of a hook being create like that::

    .. code-block:: python

        from granola.hooks.base_hook import register_hook

        @register_hook(hook_enum=HookTypes.post_reading, hooked_classes=[CannedQueries])
        def LoopCannedQueries(hooked, result, data, **kwargs):
            if result is SENTINEL:
                hooked._start_serial_generator(data)
                result = next(hooked.serial_generator[data])
                return result
            return result

This is the actual implementation of the looping hook that by default loops all canned queries
(minus the docstring), you can find the documentation for that hook at the bottom of this page.

``register_hook`` takes two arguments, the ``hook_type_enum``, which tells you if it is a pre or
post_reading hook (can be passed in as a direct enum object or as a string), and the ``hooked_classes``,
which tell you which classes the hook applies to. After that is just your function definition,
which the arguments for that follow the ``post_reading`` method for :class:`~granola.hooks.base_hook.BaseHook`.

After you have "registered" your hook function, it can then be initialized like a hook class.
(i.e. substantiating it before you pass it to ``Cereal``). If you don't instantiate it, then Cereal
will instantiate it with default arguments, this allows you to treat it as a regular function being passed
into ``Cereal``, and not worry about what else happens with the decorator

******************
Hook Examples
******************

.. code-block:: python

    >>> # this way works by initializing LoopCannedQueries to non default values
    >>> hook = LoopCannedQueries(attributes={"get batt\r"}, include_or_exclude="include")
    >>> bk_cereal = Cereal(some_config, hooks=[hook])

    >>> # This version we initialize it to its default values
    >>> hook = LoopCannedQueries()
    >>> bk_cereal = Cereal(some_config, hooks=[hook])

    >>> # This version we don't initialize it at all and let Cereal initialize it to its default values
    >>> bk_cereal = Cereal(some_config, hooks=[LoopCannedQueries])

This last example also shows how to pass hooks to ``Cereal``. You pass hooks in an iterable to
``Cereal``, and ``Cereal`` will associate the hook with whatever class it needs to
based on the classes listed in your hook's ``hooked_classes``. In these example, ``LoopCannedQueries`` would
only run on ``CannedQueries``, but ``MyHook`` would run on ``CannedQueries`` and ``GettersAndSetters``.

One final note, SENTINEL is a special book keeping object for special unhandled responses that is different
from a None response.
"""
