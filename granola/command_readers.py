import abc
import copy
import inspect
import logging
import os
import random
import re
from collections import OrderedDict
from pathlib import Path

import jinja2
import jinja2.meta
import pandas as pd

import granola.hooks
from granola.enums import RandomizeResponse, get_attribute_from_enum, validate_enum
from granola.hooks.base_hook import wrap_in_hooks
from granola.utils import ABC, IS_PYTHON3, SENTINEL, fixpath, load_serial_df

logger = logging.getLogger(__name__)


class SerialCmds(object):
    """
    Serial Command DataFrame container object. Required columns for DataFrame are `cmd` and `response`,
    Other columns are optional, and may or may not be used by certain Command Readers.

    Args:
        data (list[pd.DataFrame]): list of DataFrames containing serial command, response pairs,
            as well potentially other columns.
        will_randomize_responses (RandomizeResponse): Whether the responses of each command will be
            randomized or not.

    See Also:

        Class :class:`~granola.command_readers.CannedQueries`

        Config guide :ref:`Canned Queries Configuration`
    """

    def __init__(self, data=None, will_randomize_responses=RandomizeResponse.not_randomized):
        self.data = data if data is not None else []  # type: list[pd.DataFrame]
        self.will_randomize_responses = get_attribute_from_enum(will_randomize_responses, "name")
        validate_enum(self.will_randomize_responses, RandomizeResponse)

    def add_dataframe(self, df):
        """Add dataframe to data"""
        self.data.append(df)

    def add_df_from_file(self, file, data_path_root=None, **kwargs):
        """
        Add a df to data from a csv file path

        Args:
            file (str): Path to csv file.
            data_path_root (str, optional): Path to configuration. Required if file path is not an absolute path
            extra_fields (dict, optional): Dictionary of extra fields to add to DataFrame of commands. Either
                key will be mapped to a new column in the DataFrame, and each value can either be
                a single value, in which case it will be broadcast to all rows. Or a list of values
                the same length as the number of rows in the data.
        """
        file = str(file)
        if not os.path.isabs(file):
            if data_path_root is None:
                raise TypeError("`data_path_root` must be specified when using a relative file path")
            data_path_root = str(data_path_root)
            file = os.path.join(os.path.dirname(data_path_root), file)
        file = fixpath(file)
        logger.debug("Canned query path %s: ", file)
        df = load_serial_df(file)
        if kwargs:
            self._append_extra_fields_to_df(df, **kwargs)
        return self.add_dataframe(df)

    def add_df_from_dict(self, dic, **kwargs):
        """
        Add a df to data from a dictionary of serial commands. The format for this dictionary
        can take a few forms. It can either be expressed in a JSON configuration or passed in python
        to Cereal. Here is the most basic form, where each command is mapped directly to a single response.

        Args:
            dic (dict): Dictionary of serial commands. See examples above for formatting.
            extra_fields (dict): Dictionary of extra fields to add to DataFrame of commands. Either
                key will be mapped to a new column in the DataFrame, and each value can either be
                a single value, in which case it will be broadcast to all rows. Or a list of values
                the same length as the number of rows in the data.
        """
        data = []
        d = copy.deepcopy(dic)
        for cmd, value in d.items():
            self._transverse_dict_and_append(data, cmd, value)
        df = pd.DataFrame.from_records(data)
        if kwargs:
            self._append_extra_fields_to_df(df, **kwargs)
        return self.add_dataframe(df)

    def _transverse_dict_and_append(self, data, cmd, value, **extra_fields):
        if isinstance(value, (str, int, float)):  # End of node
            self._append_to_list_of_rows(data, cmd, value, **extra_fields)
            return

        inner_extra_fields, response = self._extract_respose(value)

        if isinstance(response, (list, tuple)):
            for index, item in enumerate(response):
                if isinstance(item, (list, tuple)):
                    resp = item[0]
                    ex_fields = item[1]

                    intersection = set(ex_fields).intersection(inner_extra_fields)
                    if intersection:
                        for field in intersection:
                            scalar = isinstance(inner_extra_fields[field], (float, str, int))
                            if not scalar:
                                raise KeyError(
                                    "Extra Fields cannot be specified for both individual commands, and as a list."
                                    "\nEither specify a extra field for individual commands"
                                    " or as a list the same length as your command responses."
                                )

                    response_ = resp
                    extra_fields_ = {
                        key: val[index] if isinstance(val, (list, tuple)) else val
                        for key, val in inner_extra_fields.items()
                    }
                    extra_fields_.update(ex_fields)
                elif isinstance(item, (str, int, float)):
                    response_ = item
                    extra_fields_ = {
                        key: val[index] if isinstance(val, (list, tuple)) else val
                        for key, val in inner_extra_fields.items()
                    }
                else:
                    raise ValueError("Invalid JSON format for canned_queries")
                self._append_to_list_of_rows(data, cmd, response_, **extra_fields_)
        else:
            response_ = response
            extra_fields_ = inner_extra_fields
            self._append_to_list_of_rows(data, cmd, response_, **extra_fields_)

    @staticmethod
    def _extract_respose(value):
        if isinstance(value, dict):
            response = value.pop("response")
        elif isinstance(value, (list, tuple)):  # value must be a list for it to be valid json
            response = list(value)  # copy to make believe that it was a dict of form {response: []}
            value = {}
        else:
            raise ValueError("Invalid JSON format for canned_queries")
        return value, response

    @staticmethod
    def _append_to_list_of_rows(data, cmd, response, **ex_fields):
        data.append(dict(cmd=cmd, response=response, **ex_fields))

    @staticmethod
    def _append_extra_fields_to_df(data, **kwargs):
        for field, value in kwargs.items():
            if field in data.columns:
                data.loc[data[field].isna(), field] = value
            else:
                data[field] = value


class InstrumentAttribute(object):
    def __init__(self, name, value, meta_data=None):
        self.name = name
        self.value = value
        self.def_value = value
        self.meta_data = meta_data if meta_data is not None else OrderedDict()


class BaseCommandReaders(ABC):
    """
    BaseCommandReaders Class that sets the interface for other CommandReaders. The basic form of
    a command reader is that Cereal will interact with it solely through its ``__init__``
    and :meth:`granola.command_readers.BaseCommandReaders.get_reading`. The ``get_reading``
    method is the method that will be called, handed in a serial command, processed in some way,
    and returned. If the Command Reader can not process the serial command, it instead returns
    None or a SENTINEL object (more on that below) to indicate that the supplied serial command
    isn't defined for that Command Reader, allowing any other Command Readers to process it instead.

    The `get_reading` commands are also decorated with @wrap_in_hooks, which will run ``_hooks_``
    attributes (of type :mod:`~granola.hooks.hooks`) that have a defined ``prehook`` method before
    ``get_reading`` and ``_hooks_`` with a defined ``posthook`` method after after ``get_reading``.

    Because "" is a valid serial command response, we use None to signify an unsupported response.
    We also have a defined SENTINEL object for response that are undefined in other ways.
    For example, Canned queries (command and response defined from list) by default loop back when
    they get to the end of the list, but if you exclude a command from that list, and then don't
    handle it another way, Instead of having undefined behavior, we return a SENTINEL object,
    which Cereal will treat as an undefined response, but also emit a warnign log message
    as well.

    Args:
        hooks(list[BaseHook], optional): List of Hooks to run on this Command Reader.
            Defaults to `[]`
        data_path_root(str | Path, optional): Path to the where all data file paths for this command reader
            (such as defining the serial commands) will be referenced from. Not every Command
            Reader, or every way to initialize a certain Command Reader uses data files, so
            this doesn't apply to every Command Reader.
            Defaults to current working directory.

    See Also
    --------
    :class:`.Cereal` : Breakfast Cereal class used for mocking
    :ref:`Custom Command Readers and Hooks Configuration` : Configuration Overview
    :ref:`Basic Overview of Mock Cereal and API` : Intro Tutorial
    """

    def __init__(self, hooks=None, data_path_root=None, *args, **kwargs):
        super(BaseCommandReaders, self).__init__()
        self._hooks_ = hooks if hooks is not None else []
        self._data_path_root = data_path_root if data_path_root is not None else os.getcwd()

    @wrap_in_hooks
    @abc.abstractmethod
    def get_reading(self, data):
        """
        Processes incoming serial command data and return a response if a matching one is found.

        Args:
            data (str): Incoming serial command

        Returns:
            str | None | SENTINEL: the response from either the matching getter or setter.
                Returns None if serial command is not supported.
                Returns SENTINEL as a flag for some kind of none processing of the serial command
                by the hooks and CommandReader, dependent on the individual CommandReader.
        """

    def register_hook(self, hook):
        self._hooks_.append(hook)

    def assign_default_hook(self):
        """If self._hooks_ hooks is empty, add any default hooks for this Command Reader."""
        if not self._hooks_:
            pass


class GettersAndSetters(BaseCommandReaders):
    """
    Command Reader to handle getters and setters. It initializes the default values and stores those
    values in the attribute `self.instrument_attributes`. These attributes can then be modified with
    setters defined in the setters in `self.setters`, and then grabbed from the getters stored in
    `self.getters`.

    Inside the getters and setters, the formatting follows Jinja2 formatting syntax.

    Args:
        arguments for BaseCommandReaders

    See Also
    --------
    :ref:`Getters and Setters Configuration`

    :ref:`Advanced Getters and Setters`
    """

    def __init__(
        self,
        default_values=None,
        getters=None,
        setters=None,
        variable_start_string="{{",
        variable_end_string="}}",
        **kwargs
    ):
        super(GettersAndSetters, self).__init__(**kwargs)
        self._variable_start_string = variable_start_string
        self._variable_end_string = variable_end_string
        self.jinja_env = jinja2.Environment(
            variable_start_string=variable_start_string,
            variable_end_string=variable_end_string,
            loader=jinja2.BaseLoader(),
        )
        default_values = default_values if default_values is not None else OrderedDict()
        getters = getters if getters is not None else OrderedDict()
        setters = setters if setters is not None else OrderedDict()
        self.instrument_attributes = OrderedDict()
        self.getters = OrderedDict()
        self.setters = OrderedDict()
        self._load_getters_and_setters(default_values, getters, setters)

    @wrap_in_hooks
    def get_reading(self, data):
        """
        Processes incoming serial command data and sends it to `self._process_getter` to see if
        it is a getter and get its response, if not, sends it to `self._process_setter`,
        to see if it is a setter and then set the respective setter and get its response,
        if not, it returns None.

        Args:
            data (str): Incoming serial command

        Returns:
            str | None: the response from either the matching getter or setter. If no matching
                getter or setter, then it returns None.
        """
        next_read = self._process_getter(data)
        if next_read is not None:
            return next_read
        next_read = self._process_setter(data)
        if next_read is not None:
            return next_read
        return

    @property
    def attribute_vals(self):
        attribute_vals = {
            attribute: instrument_attribute.value
            for attribute, instrument_attribute in self.instrument_attributes.items()
        }
        return attribute_vals

    def render_template(self, string, attribute_vals=None):
        attribute_vals = attribute_vals if attribute_vals is not None else self.attribute_vals
        command = string.replace("\r", "_\\r_").replace("\n", "_\\n_")
        template = self.jinja_env.from_string(command)
        result = template.render(**attribute_vals).replace("_\\r_", "\r").replace("_\\n_", "\n")
        return result

    def _load_getters_and_setters(self, default_values, getters, setters):
        """Loads default values, getters and setters"""

        if not default_values:
            return
        self._initialize_default_instrument_attributes(default_values)
        self._initialize_getters(getters)
        self._initialize_setters(setters)

    def _initialize_default_instrument_attributes(self, default_values):
        """Loads default values into `self.instrument_attributes`"""
        for attribute, default_value in default_values.items():
            self.instrument_attributes[attribute] = InstrumentAttribute(name=attribute, value=default_value)

    def _initialize_getters(self, getters):
        """
        Loads all getters from getters_and_setters["getters"] into `self.getters`. If getter
        does not get an attribute in self.instrument_attributes, raise Value Error"""
        for getter in getters:
            self._check_attributes_are_valid("getters", getter)

            self.getters[getter["cmd"]] = getter["response"]

    def _initialize_setters(self, setters):
        """
        Loads all setters from getters_and_setters["setters"] into `self.setters`. If setter
        does not get an attribute in self.instrument_attributes, raise Value Error"""
        for setter in setters:
            self._check_attributes_are_valid("setters", setter)

            regex = "{variable_start}(.*?){variable_end}".format(
                variable_start=self._variable_start_string, variable_end=self._variable_end_string
            )
            setter_regex = re.sub(regex, self._format_match_group, setter["cmd"])
            self.setters[setter_regex] = setter["response"]

    def _format_match_group(self, match):
        """
        Get and format match group. Default formatters create named match groups to
        extract the match group by the name of the attribute later for easier book keeping."""
        group = match.group(0)
        group = (
            group.strip(self._variable_start_string)
            .strip(
                self._variable_end_string,
            )
            .strip()
        )
        group = "(?P<{group}>.*)".format(group=group)
        return group

    def _process_getter(self, data):
        """Process getter if data matches getter format"""
        if data in self.getters:
            next_read = self.render_template(self.getters[data])

            return next_read
        return

    def _process_setter(self, data):
        """Process setter if data matches a setter regex"""
        regex_match, response_template = self._get_matching_setter(data)
        if not response_template:
            return
        self._proccess_setter_helper(regex_match, self.attribute_vals)

        response = self.render_template(response_template)
        return response

    def _get_matching_setter(self, data):
        """Process setter if data matches a setter regex"""
        for cmd_regex, response in self.setters.items():
            regex_match = re.search(cmd_regex, data)
            if regex_match:
                return regex_match, response

        return None, None

    def _proccess_setter_helper(self, regex_match, attributes):
        # we can extract the match group by name because we gave
        # them a name earlier for ease of book keeping now
        for attribute in attributes:
            try:  # check for all attributes, only update attribute that matches regex
                updated_value = regex_match.group(attribute)
            except IndexError:
                continue

            logger.debug("Updating %s to %s", attribute, updated_value)

            self.instrument_attributes[attribute].value = updated_value

    def _check_attributes_are_valid(self, attribute_type, template_string):
        """Check every attribute in attributes is an attribute in `self.instrument_attributes`,
        else raise ValueError"""
        for template in template_string.values():
            parsed_content = self.jinja_env.parse(template)
            attributes = jinja2.meta.find_undeclared_variables(parsed_content)
            for attribute in attributes:
                if attribute not in self.instrument_attributes:
                    raise ValueError(
                        "{attribute_type} attribute {attribute} not found in default_values."
                        "\nMake sure you initialize all values!"
                        "\nProblem string: {template_string}".format(
                            attribute_type=attribute_type, attribute=attribute, template_string=template
                        )
                    )


class CannedQueries(BaseCommandReaders):
    """
    Helper class that processes canned queries (queries defined ahead of time from a list
    such as a csv or configuration dictionary).

    It stores a dictionary of :class:`~granola.command_readers.SerialCmds`, which represents
    canned queries as pandas DataFrames of the serial commands. And then as a serial command comes in,
    it is directed to the correct :class:`~granola.command_readers.SerialCmds` and then creates a slice of
    your DataFrame to get only the matching serial commands to iterate over.

    See Also
    --------
    :ref:`Canned Queries Configuration` for examples on configuration formatting.

    :ref:`Custom Command Readers and Hooks Configuration` : Command Readers and Hook Overviews
    """

    def __init__(self, data=None, data_path_root=None, **kwargs):

        super(CannedQueries, self).__init__(data_path_root=data_path_root, **kwargs)
        self.data = data if data is not None else OrderedDict()
        self.serial_df = pd.DataFrame(columns=["cmd", "response"])  # default empty df
        serial_cmd_files_kwargs = self._extract_serial_cmd_file_kw_from_config(kwargs)
        self.serial_cmd_file = SerialCmds(**serial_cmd_files_kwargs)
        self.serial_generator = OrderedDict()

        for maybe_file in self.data:
            if isinstance(maybe_file, (str, Path)):
                self.serial_cmd_file.add_df_from_file(maybe_file, self._data_path_root, **kwargs)
            elif isinstance(maybe_file, dict):
                self.serial_cmd_file.add_df_from_dict(maybe_file, **kwargs)

        self._seed_serial_dfs()

    def assign_default_hook(self):
        if not self._hooks_:
            self._hooks_ = [granola.hooks.hooks.LoopCannedQueries()]

    @wrap_in_hooks
    def get_reading(self, data):
        """
        Process incoming canned queries by extracting just the serial commands that match the
        incoming serial command and then create a generator of those matching serial commands
        and response to iterate through.

        Args:
            data (str): Incoming serial command

        Returns:
            str | None | SENTINEL: the response from matching serial df.
            If no matching matching command is found, then it returns None.
            If The generator is exhausted, and no Hook is activate to reseed the generator or
            alter the behavior in some other way, return SENTINEL.

        See Also
        --------
        :mod:`Hooks <granola.hooks.hooks>` : Hook API information

        :ref:`Canned Queries Configuration` for examples on configuration formatting.

        :ref:`Custom Command Readers and Hooks Configuration` : Command Readers and Hook Overviews
        """
        try:
            if data not in self.serial_generator:
                self._start_serial_generator(data)
            next_read = next(self.serial_generator[data], SENTINEL)
        except KeyError:
            next_read = None
        return next_read

    def _start_serial_generator(self, cmd):
        serial_df = self._filter_serial_df(cmd=cmd)  # type: pd.DataFrame
        if not serial_df.empty:
            serial_df_generator = self._get_generator_from_df(serial_df, self.serial_cmd_file.will_randomize_responses)
            self.serial_generator[cmd] = serial_df_generator

    def _extract_serial_cmd_file_kw_from_config(self, kw):
        """
        extract signature of SerialCmds and recursively search `self._config` for matching
        keys ad return all found key value pairs.
        """
        if IS_PYTHON3:  # pragma: no cover
            inspection_getargspec = inspect.getfullargspec
        else:
            inspection_getargspec = inspect.getargspec
        kwargs = OrderedDict()
        serial_cmd_args = inspection_getargspec(SerialCmds.__init__).args
        for arg in serial_cmd_args:
            if kw.get(arg) is not None:
                kwargs[arg] = kw[arg]
            if kw.get("canned_queries", {}).get(arg) is not None:
                kwargs[arg] = kw["canned_queries"][arg]
        logger.debug("%s extracted SerialCmds kwargs: %s", self, kwargs)
        return kwargs

    def _seed_serial_dfs(self):
        if self.serial_cmd_file.data:
            self.serial_df = pd.concat(objs=[df for df in self.serial_cmd_file.data])

    def _filter_serial_df(self, cmd):
        """
        Filter DataFrame to only the commands that match the inputted command

        This allows the CSVs to contain many different serial inputs, but it will only return
        the serial command that you pass in.

        Args:
            df (pd.DataFrame): DataFrame to filer.
            cmd (str): Command to filter against.

        Returns:
            pd.DataFrame: Filtered DataFrame.
        """
        df = self.serial_df
        conditions = df["cmd"] == cmd
        columns = ["response"]
        serial_df = df.loc[conditions, columns]
        return serial_df

    @staticmethod
    def _get_generator_from_df(df, will_randomize_responses):
        """Create a generator for the df so that when you call next on that generator, it
        gives you the next serial command each time, and not the first one. Allowing you to
        continue through the list of serial commands. Also gives the option to randomize results.

        Args:
            df (pd.DataFrame): DataFrame to iterate over
            serial_cmd_file (SerialCmds): SerialCmds to know if you are randomizing the results or just doing
                a straight iteration.
        """
        # TODO(madeline) only pass in randomize enum? Also clean up and make subfunctions?
        if will_randomize_responses == RandomizeResponse.not_randomized.name:
            for _, rows in df.iterrows():
                yield rows["response"]
        if (
            will_randomize_responses == RandomizeResponse.randomized_w_replacement.name
            or will_randomize_responses == RandomizeResponse.randomize_and_remove.name
        ):
            while df.shape[0] > 0:
                df_length = df.shape[0]
                row = random.randint(0, df_length - 1)
                yield df["response"].iloc[row]
                if will_randomize_responses == RandomizeResponse.randomize_and_remove.name:
                    df = df.drop(row)


__doc__ = """
Command Readers are the objects that handle the processing of individual serial
commands. Each serial command that comes in is processed by each Command Reader and
once a Command Reader returns a valid response, the next Command Readers will skip processing the command.
This allows you to change the behavior of individual commands by defining new Command Readers.
"""
