"""
This module is deprecated and will be removed in version 1.0. Please use  :mod:`~granola.breakfast_cereal` instead
"""
from granola.breakfast_cereal import Cereal
from granola.command_readers import DefaultDF, DeprecatedDefaultDF
from granola.utils import deprecation


class MockSerial(Cereal):
    def __init__(self, config_key, config_path="config.json", command_readers=None, hooks=None):
        deprecation("MockSerial is deprecated. Please use granola.breakfast_cereal.Cereal instead.", "1.0")

        config = self._load_config(config_key=config_key, config_path=config_path)

        config = self._check_and_normalize_config_deprecation(config)

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
            cq = config.pop("canned_queries")
            command_readers["CannedQueries"] = cq

            cq = command_readers["CannedQueries"]

            if "files" in cq:
                deprecation("canned_queries key 'files' has been deprecated. Use the key 'data' instead.", "1.0")
                cq["data"] = cq.pop("files")

            if DeprecatedDefaultDF in cq.get("data", {}):
                deprecation(
                    "command_readers['CannedQueries']['data'] key '_default_csv_' has been deprecated,"
                    " Use '`DEFAULT`' instead",
                    "1.0",
                )
                cq["data"][DefaultDF] = cq["data"].pop(DeprecatedDefaultDF)

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
                    "'GettersAndSetters' variable declaration may follow old format"
                    "\nEither switch to traditional jinja2 formatting ({{ var }})"
                    "\nor specify explicitly your variable_start_string and variable_end_string inside"
                    " getters and setters (ex: 'variable_start_string': '`')",
                    "1.0",
                )
                getters_and_setters["variable_start_string"] = "`"
                getters_and_setters["variable_end_string"] = "`"
            gs = config.pop("getters_and_setters")
            command_readers["GettersAndSetters"] = gs

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
                    setter["cmd"] = setter.pop("setter")

        return config
