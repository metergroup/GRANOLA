"""
This module is deprecated and will be removed in version 1.0. Please use  :mod:`~granola.breakfast_cereal` instead
"""
from granola.breakfast_cereal import Cereal
from granola.command_readers import DefaultDF, DeprecatedDefaultDF
from granola.utils import deprecation


class MockSerial(Cereal):
    """
    Deprecated version of :class:`~granola.breakfast_cereal.Cereal`. Will be removed in 1.0

    Switch to using :class:`~granola.breakfast_cereal.Cereal` and the new interface.
    """

    def __init__(self, config_key, config_path="config.json", command_readers=None, hooks=None):
        deprecation("MockSerial is deprecated. Please use granola.breakfast_cereal.Cereal instead.", "1.0")
        command_readers = command_readers or []
        hooks = hooks or []
        config = self._load_config(config_key=config_key, config_path=config_path)

        config = self._check_and_normalize_config_deprecation(config)

        config = self._check_and_normalize_command_readers_deprecations(config, command_readers)
        config = self._check_and_normalize_hook_deprecations(config, hooks)

        super(MockSerial, self).__init__(config_path=config_path, **config)

    def _check_and_normalize_config_deprecation(self, config):
        command_readers = config.setdefault("command_readers", {})
        if "canned_queries" in config:
            deprecation(
                "Specifically CannedQueries Command Reader through the outermost config key 'canned_queries"
                " is deprecated. Please use the 'command_reader' section instead."
                " See https://granola.readthedocs.io/en/latest/config/config.html for more details.",
                "1.0",
            )
            # swap canned_queries for "command_readers": {"CannedQueries": ...}
            command_readers["CannedQueries"] = config.pop("canned_queries")

            cr = command_readers["CannedQueries"]

            if "files" in cr:
                deprecation("canned_queries key 'files' has been deprecated. Use the key 'data' instead.", "1.0")
                # swap file key for data
                cr["data"] = cr.pop("files")

            if DeprecatedDefaultDF in cr.get("data", {}):
                deprecation(
                    "canned_queries['data'] key '_default_csv_' has been deprecated," " Use '`DEFAULT`' instead",
                    "1.0",
                )
                # swap deprecated default df key for default df key
                cr["data"][DefaultDF] = cr["data"].pop(DeprecatedDefaultDF)

        if "getters_and_setters" in config:
            deprecation(
                "Specifically GettersAnd_setters Command Reader through the outermost config key"
                " 'getters_and_setters is deprecated. Please use the 'command_reader' section instead."
                " See https://granola.readthedocs.io/en/latest/config/config.html for more details."
            )

            # Check for old form of variable substitution pre jinja
            getters_and_setters = config["getters_and_setters"]
            start_not_in = "variable_start_string" not in getters_and_setters
            end_not_in = "variable_end_string" not in getters_and_setters
            if start_not_in and end_not_in:
                deprecation(
                    "'GettersAndSetters' variable declaration follows old format"
                    "\nSwitch to using ``Cereal``, which defaults to traditional jinja2 formatting ({{ var }}),"
                    "\nor specify explicitly your variable_start_string and variable_end_string inside"
                    " getters and setters (ex: 'variable_start_string': '`')",
                    "1.0",
                )
                # specify getters and setters variable start and end as the old way
                getters_and_setters["variable_start_string"] = "`"
                getters_and_setters["variable_end_string"] = "`"

            # swap canned_queries for "command_readers": {"CannedQueries": ...}
            command_readers["GettersAndSetters"] = config.pop("getters_and_setters")

            getters = command_readers["GettersAndSetters"].get("getters", [])
            for getter in getters:
                if "getter" in getter:
                    deprecation(
                        "Using 'getter' key inside"
                        " config['getters_and_setters']['getters']['getter']"
                        "is deprecated and will be removed in a future release."
                        "\nSwitch to using the key 'cmd' instead.",
                        "1.0",
                    )
                    # swap getters key for cmd
                    getter["cmd"] = getter.pop("getter")
            setters = command_readers["GettersAndSetters"].get("setters", [])
            for setter in setters:
                if "setter" in setter:
                    deprecation(
                        "Using 'setter' key inside "
                        " config['getters_and_setters']['setters']['setter']"
                        "is deprecated and will be removed in a future release."
                        "\nSwitch to using the key 'cmd' instead.",
                        "1.0",
                    )
                    # swap setters key for cmd
                    setter["cmd"] = setter.pop("setter")

        return config

    def _check_and_normalize_command_readers_deprecations(self, config, command_readers):
        config_readers = config["command_readers"]
        for command_reader in command_readers:
            str_not_in = command_reader not in config_readers
            obj_not_in = getattr(command_reader, "__name__", "") not in config_readers
            cls_not_in = command_reader.__class__.__name__ not in config_readers
            if str_not_in and obj_not_in and cls_not_in:
                config["command_readers"][command_reader] = {}
        return config

    def _check_and_normalize_hook_deprecations(self, config, hooks):
        config_hooks = config.setdefault("hooks", {})
        for hook in hooks:
            str_not_in = hook not in config_hooks
            obj_not_in = getattr(hook, "__name__", "") not in config_hooks
            cls_not_in = hook.__class__.__name__ not in config_hooks
            if str_not_in and obj_not_in and cls_not_in:
                config["hooks"][hook] = {}
        return config
