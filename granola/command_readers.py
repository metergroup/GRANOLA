import abc
import copy
import inspect
import logging
import os
import random
import re
from collections import OrderedDict
from pathlib import Path

import attr
import jinja2
import jinja2.meta
import pandas as pd

from granola.hooks.base_hook import wrap_in_hooks
from granola.utils import (
    ABC,
    IS_PYTHON3,
    SENTINEL,
    deprecation,
    fixpath,
    load_serial_df,
)

try:
    from enum import Enum, auto
except ImportError:
    from aenum import Enum, auto

logger = logging.getLogger(__name__)

DefaultDF = "`DEFAULT`"  # Default dataframe key
DeprecatedDefaultDF = "_default_csv_"  # Default dataframe key


class RandomizeResponse(Enum):
    """Randomize response enum"""

    not_randomized = auto()  # Don't randomize
    randomized = auto()  # Randomize and replace
    randomized_and_remove = auto()  # Randomize and remove


@attr.s
class SerialCmds(object):
    """
    Serial Command DataFrame container object. Required columns for DataFrame are `cmd` and `response`,
    Other columns are optional, and may or may not be used by certain Command Readers.

    Args:
        data (pd.DataFrame): DataFrame containing serial command, response pairs, as well potentially other
            columns.

        --- Not currently being used ---
        will_randomize_responses (RandomizeResponse): Whether the responses of each command will be
            randomized or not.

    See Also:

        Class :class:`~granola.command_readers.CannedQueries`

        Config guide :ref:`Canned Queries Configuration`
    """

    data = attr.ib(type=pd.DataFrame)
    will_randomize_responses = attr.ib(
        type=RandomizeResponse,
        default=RandomizeResponse.not_randomized,
    )

    @classmethod
    def from_file(cls, file, config_path=None, **kwargs):
        """
        Generate a `SerialCmds` from a csv file path

        Args:
            file (str): Path to csv file. Required
            config_path (str): Path to configuration. Required if file path is not an absolute path
            extra_fields (dict): Dictionary of extra fields to add to DataFrame of commands. Either
                key will be mapped to a new column in the DataFrame, and each value can either be
                a single value, in which case it will be broadcast to all rows. Or a list of values
                the same length as the number of rows in the data.
        """
        file = str(file)
        if not os.path.isabs(file):
            if config_path is None:
                raise TypeError("`config_path` must be specified when using a relative file path")
            config_path = str(config_path)
            file = os.path.join(os.path.dirname(config_path), file)
        file = fixpath(file)
        logger.debug("Canned query path %s: ", file)
        df = load_serial_df(file)
        if kwargs:
            cls._append_extra_fields_to_df(df, **kwargs)
        return cls(data=df)

    @classmethod
    def from_dict(cls, dic, **kwargs):
        """
        Generate a `SerialCmds` from a dictionary of serial commands. The format for this dictionary
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
            cls._transverse_dict_and_append(data, cmd, value)
        df = pd.DataFrame.from_records(data)
        if kwargs:
            cls._append_extra_fields_to_df(df, **kwargs)
        return cls(data=df)

    @classmethod
    def _transverse_dict_and_append(cls, data, cmd, value, **extra_fields):
        if isinstance(value, (str, int, float)):  # End of node
            cls._append_to_list_of_rows(data, cmd, value, **extra_fields)
            return

        inner_extra_fields, response = cls._extract_respose(value)

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
                cls._append_to_list_of_rows(data, cmd, response_, **extra_fields_)
        else:
            response_ = response
            extra_fields_ = inner_extra_fields
            cls._append_to_list_of_rows(data, cmd, response_, **extra_fields_)

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
    a command reader is that Cereal will interact with it solely through `initialize_config`
    and `get_reading`. `initialize_config` happens durring Cereal's `__init__` method where
    it passes its config to the CommandReader. The CommandReader is the able to parse out whatever
    parameter's it needs from said config. And then in `get_reading`, Cereal passes in the
    serial command and the CommandReader processes it however it does, and returns it.

    The `get_reading` commands are also decorated with @wrap_hooks, which will run the attributes
    `pre_hooks` (iterable type of functions) before `get_reading` and
    `post_hooks` (iterable type of functions) after `get_reading`, allowing you to modify the
    behavior of the `get_reading` method for certain serial commands.

    Because "" is a valid serial command response, we use None to signify an unsupported response.
    We also have a defined SENTINEL object for response that are undefined in other ways.
    For example, Canned queries (command and response defined from list) by default loop back when
    they get to the end of the list, but if you exclude a command from that list, and then don't
    handle it another way, Instead of having undefined behavior, we return a SENTINEL object,
    which Cereal will treat as an undefined response, but also emit a warnign log message
    as well.

    Args:
        pre_hooks (list or tuple): iterable of hooks to run before `get_readings`
        post_hooks (list or tuple): iterable of hooks to run after `get_readings`
    """

    def __init__(self, config_path=None, hooks=None, *args, **kwargs):
        super(BaseCommandReaders, self).__init__()
        self._config_path = config_path if config_path is not None else os.getcwd()
        self._hooks_ = hooks if hooks is not None else []

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
            ...


class GettersAndSetters(BaseCommandReaders):
    """
    Helper class that processes getters and setters. It initializes the default values set
    in the config and stores those values in the attribute `self.instrument_attributes`. These
    attributes can then be modified with setters defined in the setters from the config and stored
    in `self.setters`, and then grabbed from the getters defined in getters from the config and
    stored in `self.getters`.

    Inside the getters and setters, the values pulled out will be the values
    inside matching backticks (`).

    Args:
        arguments for BaseCommandReaders
    """

    def __init__(
        self, default_values=None, getters=None, setters=None, variable_start_string="{{", variable_end_string="}}", **kwargs
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

    @classmethod
    def _from_config(cls, config, **kwargs):
        getters_and_setters = config.get("getters_and_setters", {})
        default_values = getters_and_setters.get("default_values", {})
        getters = getters_and_setters.get("getters", {})
        setters = getters_and_setters.get("setters", {})
        variable_start_string = getters_and_setters.get("variable_start_string", "{{")
        variable_end_string = getters_and_setters.get("variable_end_string", "}}")
        return cls(default_values, getters, setters, variable_start_string, variable_end_string, **kwargs)

    @wrap_in_hooks
    def get_reading(self, data):
        """
        Processes incoming serial command data and sends it to `self._process_getter` to see if
        it is a getter and get its response, if not, sends it to `self._process_setter`,
        to see if it is a setter and get its response, if not, it returns None.

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
            if "getter" in getter:
                deprecation(
                    "Using 'getter' key inside 'getter_and_setters'"
                    "(config['getters_and_setters']['getters']['getter']"
                    "is deprecated and will be removed in a future release."
                    "\nSwitch to using the key 'cmd' instead."
                )
                getter["cmd"] = getter.pop("getter")

            self._check_attributes_are_valid("getters", getter)

            self.getters[getter["cmd"]] = getter["response"]

    def _initialize_setters(self, setters):
        """
        Loads all setters from getters_and_setters["setters"] into `self.setters`. If setter
        does not get an attribute in self.instrument_attributes, raise Value Error"""
        for setter in setters:
            if "setter" in setter:
                deprecation(
                    "Using 'setter' key inside 'getter_and_setters'"
                    "(config['getters_and_setters']['setters']['setter']"
                    "is deprecated and will be removed in a future release."
                    "\nSwitch to using the key 'cmd' instead."
                )
                setter["cmd"] = setter.pop("setter")
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
    such as a csv).

    It stores a dictionary of :class:`~granola.command_readers.SerialCmds`, which represents
    canned queries as pandas DataFrames of the serial commands. And then as a serial command comes in,
    it is directed to the correct :class:`~granola.command_readers.SerialCmds` and then creates a slice of
    your DataFrame to get only the matching serial commands to iterate over.

    See :ref:`Canned Queries Configuration` for examples on configuration formatting.
    """

    def __init__(self, data=None, config_path=None, **kwargs):

        super(CannedQueries, self).__init__(config_path=config_path, **kwargs)
        self.data = data if data is not None else OrderedDict()
        self.serial_cmd_files = OrderedDict()
        self.serial_dfs = OrderedDict()
        self.serial_generator = OrderedDict()

        if DeprecatedDefaultDF in self.data:
            deprecation("canned_queries['data'] key '_default_csv_' has been deprecated, Use '`DEFAULT`'")
            default = self.data.pop(DeprecatedDefaultDF)
            self.data[DefaultDF] = default

        for key, maybe_file in self.data.items():
            if isinstance(maybe_file, (str, Path)):
                self.serial_cmd_files[key] = SerialCmds.from_file(maybe_file, config_path, **kwargs)
            elif isinstance(maybe_file, dict):
                self.serial_cmd_files[key] = SerialCmds.from_dict(maybe_file, **kwargs)

        self._seed_serial_dfs()

    @classmethod
    def _from_config(cls, config, config_path=None, **kwargs):
        canned_queries = config.get("canned_queries", {})

        if "files" in canned_queries and isinstance(canned_queries["files"], dict):
            deprecation("canned_queries key 'files' has been deprecated. Use the key 'data' instead.")
            data = canned_queries.pop("files")
            canned_queries["data"] = data

        kwargs.update({key: item for key, item in canned_queries.items() if key != "data"})
        data = canned_queries.get("data", {})
        return cls(data, config_path, **kwargs)

    def assign_default_hook(self):
        if not self._hooks_:
            from granola.hooks.hooks import LoopCannedQueries

            self._hooks_ = [LoopCannedQueries()]

    @wrap_in_hooks
    def get_reading(self, data):
        """
        Process incoming canned queries and route them to the appropriate df and create
        a generator of that df queries to iterate through them.

        Args:
            data (str): Incoming serial command

        Returns:
            str | None: the response from matching serial df. If no matching matching command is found,
            then it returns None.
        """
        try:
            if data not in self.serial_generator:
                self._start_serial_generator(data)
            next_read = next(self.serial_generator[data], SENTINEL)
        except KeyError:
            next_read = None
        return next_read

    def _start_serial_generator(self, cmd):
        df, serial_cmd_file = self._get_matching_df(cmd)
        serial_df = self._filter_serial_df(df=df, cmd=cmd)  # type: pd.DataFrame
        if not serial_df.empty:
            serial_df_generator = self._get_generator_from_df(serial_df, serial_cmd_file)
            self.serial_generator[cmd] = serial_df_generator

    def _load_canned_queries(self, config_path):

        canned_queries = self._config.get("canned_queries", {})

        if "files" in canned_queries and isinstance(canned_queries["files"], dict):
            deprecation("canned_queries key 'files' has been deprecated. Use the key 'data' instead.")
            data = canned_queries.pop("files")
            canned_queries["data"] = data

        extra_fields = {key: item for key, item in canned_queries.items() if key != "data"}

        data = canned_queries.get("data", {})

        if DeprecatedDefaultDF in data:
            deprecation("canned_queries['data'] key '_default_csv_' has been deprecated, Use '`DEFAULT`'")
            default = data.pop(DeprecatedDefaultDF)
            data[DefaultDF] = default

        for key, maybe_file in canned_queries.get("data", {}).items():
            if isinstance(maybe_file, (str, Path)):
                self.serial_cmd_files[key] = SerialCmds.from_file(maybe_file, config_path, extra_fields=extra_fields)
            elif isinstance(maybe_file, dict):
                self.serial_cmd_files[key] = SerialCmds.from_dict(maybe_file, extra_fields=extra_fields)

    def _extract_serial_cmd_file_kw_from_config(self):
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
            if self._config.get(arg) is not None:
                kwargs[arg] = self._config[arg]
            if self._config.get("canned_queries", {}).get(arg) is not None:
                kwargs[arg] = self._config["canned_queries"][arg]
        logger.debug("%s extracted SerialCmds kwargs: %s", self, kwargs)
        return kwargs

    def _seed_serial_dfs(self):
        if self.serial_cmd_files:
            self.serial_dfs = OrderedDict(
                (key, serial_cmd_file.data) for key, serial_cmd_file in self.serial_cmd_files.items()
            )
        else:
            self.serial_dfs[DefaultDF] = pd.DataFrame(columns=["cmd", "response"])

    def _get_matching_df(self, cmd):
        """
        Get matching DataFrame from cmd by regex search.

        Each DataFrame in `self.serial_df` has a key that is a regex corresponding to what commands
        they map to. If that matches, return that DataFrame.

        Args:
            cmd (AnyStr): Command to compare against.

        Returns:
            Tuple[pd.DataFrame, SerialCmds]: Returns matching DataFrame,
                otherwise it returns default values.

        Raises:
            KeyError if cmd is never found is not found in DataFrames in no DefaultDF is defined.
        """
        for key, df in self.serial_dfs.items():
            not_default_df = key != DefaultDF
            if not_default_df and re.match(key, cmd):
                return df, self.serial_cmd_files[key]
        return self.serial_dfs[DefaultDF], self.serial_cmd_files[DefaultDF]

    @staticmethod
    def _filter_serial_df(df, cmd):
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
        conditions = df["cmd"] == cmd
        columns = ["response"]
        serial_df = df.loc[conditions, columns]
        return serial_df

    @staticmethod
    def _get_generator_from_df(df, serial_cmd_file):
        """Create a generator for the df so that when you call next on that generator, it
        gives you the next serial command each time, and not the first one. Allowing you to
        continue through the list of serial commands. Also gives the option to randomize results.

        Args:
            df (pd.DataFrame): DataFrame to iterate over
            serial_cmd_file (SerialCmds): SerialCmds to know if you are randomizing the results or just doing
                a straight iteration.
        """
        # TODO(madeline) only pass in randomize enum? Also clean up and make subfunctions?
        if serial_cmd_file.will_randomize_responses == RandomizeResponse.not_randomized:
            for _, rows in df.iterrows():
                yield rows["response"]
        if (
            serial_cmd_file.will_randomize_responses == RandomizeResponse.randomized
            or serial_cmd_file.will_randomize_responses == RandomizeResponse.randomized_and_remove
        ):
            while df.shape[0] > 0:
                df_length = df.shape[0]
                row = random.randint(0, df_length - 1)
                yield df["response"].iloc[row]
                if serial_cmd_file.will_randomize_responses == RandomizeResponse.randomized_and_remove:
                    df = df.drop(row)
