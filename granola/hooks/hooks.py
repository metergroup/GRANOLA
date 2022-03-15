import datetime
import time
from math import pi

import attr
import numpy as np

from granola.command_readers import CannedQueries, GettersAndSetters
from granola.enums import HookTypes, SetRelationship
from granola.hooks.base_hook import BaseHook, register_hook
from granola.utils import SENTINEL


@attr.s
class _ApproachHookAttributes(object):
    start_value = attr.ib(type=str, default=None, converter=float)
    end_value = attr.ib(type=str, default=None, converter=float)
    set_time = attr.ib(type=datetime.datetime, default=None)
    transition_time = attr.ib(type=int, default=None)


class ApproachHook(BaseHook):
    """
    Hook that will on applicable attributes, when a new value is set, it will approach that
    value over a period time (dictated by `transition_asc_scaling` and `transition_dsc_scaling`).
    It uses a hyperbolic tangent function to allow smooth transition from start and end values.

    Args:
        attributes (set, optional): getter and setter attributes to include or exclude from
            this hook.
        include_or_exclude (SetRelationship or str, optional): Whether to include `attributes` in
            the hook or exclude `attributes` from the hook.
        transition_asc_scaling (float): An increase of delta (change) of 1 unit takes this many seconds
            longer to transition. Must be
            positive.
        transition_dsc_scaling (float): A decrease of delta (change) of 1 unit takes this many seconds
            longer to transition. Must be
            negative.
    """

    hooked_classes = [GettersAndSetters]

    def __init__(
        self,
        attributes=None,
        include_or_exclude=SetRelationship.exclude,
        transition_asc_scaling=40,
        transition_dsc_scaling=100,
    ):
        super(ApproachHook, self).__init__(attributes=attributes, include_or_exclude=include_or_exclude)
        self.transition_asc_scaling = transition_asc_scaling
        self.transition_dsc_scaling = transition_dsc_scaling

        if self.transition_asc_scaling <= 0 or self.transition_dsc_scaling <= 0:
            raise ValueError("Inappropriate transition scaling value!")

    def pre_reading(self, hooked, data, **kwargs):
        """
        On applicable attributes, record meta data about the pre_reading value, the end_value,
        how long it should take to complete the transition, and when the transition started. Store
        all of this information in a meta data class.

        Args:
            hooked (GettersAndSetters): instance of hooked class
            data (str): Serial command
        """
        regex_match, response = hooked._get_matching_setter(data)
        if not response:
            return
        self._process_setter_approach_hook_helper(hooked, regex_match, hooked.attribute_vals)

    def post_reading(self, hooked, result, data, **kwargs):
        """
        On applicable attributes, retrieve meta data class information set from pre_reading hook,
        and based on that information (how long it has been since the set time, how long the
        transition is supposed to take, etc), calculate the new attribute value and return it.

        Args:
            hooked (GettersAndSetters): instance of hooked class
            result (str): Returned result from serial command.
            data (str): Serial command
        """
        if data in hooked.getters:
            attribute_vals = hooked.attribute_vals
            for attribute in attribute_vals:
                attrib = hooked.instrument_attributes[attribute].meta_data.get(_ApproachHookAttributes.__name__)
                if attrib:
                    seconds_ran = time.time() - attrib.set_time
                    value = attrib.start_value + 0.5 * (1 + np.tanh(6 * seconds_ran / attrib.transition_time - pi)) * (
                        attrib.end_value - attrib.start_value
                    )
                    attribute_vals[attribute] = value

            result = hooked.render_template(hooked.getters[data], attribute_vals)
        return result

    def _process_setter_approach_hook_helper(self, hooked, regex_match, attributes):
        """
        we can extract the match group by name because we gave
        them a name earlier for ease of book keeping now
        """
        for attribute in attributes:
            try:  # check for all attributes, only update attribute that matches regex
                end_value = regex_match.group(attribute)
            except IndexError:
                continue
            in_attribs = attribute in self.attributes
            include_attribs = self.include_or_exclude == SetRelationship.include.name
            exclude_attribs = self.include_or_exclude == SetRelationship.exclude.name
            if (in_attribs and include_attribs) or (not in_attribs and exclude_attribs):

                self.validate_attribute_type(hooked, attribute)

                attrib = _ApproachHookAttributes(
                    start_value=hooked.instrument_attributes[attribute].value, end_value=end_value, set_time=time.time()
                )

                delta = attrib.end_value - attrib.start_value
                transition_time = (
                    delta * self.transition_asc_scaling if delta >= 0 else delta * self.transition_dsc_scaling
                )
                attrib.transition_time = transition_time

                hooked.instrument_attributes[attribute].meta_data[_ApproachHookAttributes.__name__] = attrib
            hooked.instrument_attributes[attribute].value = end_value

    def validate_attribute_type(self, hooked, attribute):
        try:
            float(hooked.instrument_attributes[attribute].value)
        except ValueError:
            raise ValueError(
                "ApproachHook can only be applied with a float attribute.\nproblem attribute: %s" % attribute
            )


@register_hook(hook_type_enum=HookTypes.post_reading, hooked_classes=[CannedQueries])
def LoopCannedQueries(hooked, result, data, **kwargs):
    """
    Loop through canned queries to run when the returned query is SENTINEL, meaning
    the CannedQuery generator reached the end.

    Args:
        hooked (CannedQueries): CannedQueries instance to run the hook on.
        result (str): Passed in result to potentially modify.
        data (str): Serial command.

    Returns:
        str: the modified or unmodified serial command result

        SENTINEL (object): if the hook is passed in object, and it not acting on this
        serial command, it will just return SENTINEL unmodified.
    """
    if result is SENTINEL:
        hooked._start_serial_generator(data)
        result = next(hooked.serial_generator[data])
        return result
    return result


@register_hook(hook_type_enum=HookTypes.post_reading, hooked_classes=[CannedQueries])
def StickCannedQueries(hooked, result, **kwargs):
    """
    Stick on the last return query when the returned query is SENTINEL, meaning
    the CannedQuery generator reached the end.

    Args:
        hooked (CannedQueries): CannedQueries instance to run the hook on.
        result (str): Passed in result to potentially modify.

    Returns:
        str: the modified or unmodified serial command result
    """
    if result is SENTINEL:
        result = getattr(hooked, "last_reading", None)
        return result
    hooked.last_reading = result
    return result


HOOKS = {cls.__name__: cls for cls in BaseHook.__subclasses__()}


__doc__ = """
Hooks provide a way to inject customizable behavior at preditermined locations.

All hooks are subclasses of :class:`~granola.hooks.base_hook.BaseHook`. There are two ways to construct
a hook. Directly as a subclass of :class:`~granola.hooks.base_hook.BaseHook` or as a
function decorated with the :func:`~granola.hooks.base_hook.register_hook` decorator that converts a
simple function into the more full featured hook class.

For a detailed comparison of constructing a hook class versus a hook by decorator

.. seealso::

    Module :mod:`Hook API <granola.hooks.base_hook>`
"""
