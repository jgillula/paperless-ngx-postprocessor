import os
import dateutil.parser
from datetime import datetime, date
from pathlib import Path

class Config:
    class OptionSpec:
        def __init__(self, default, argparse_args):
            self.default = default
            self.argparse_args = argparse_args

            if "help" in self.argparse_args:
                self.argparse_args["help"] = self.argparse_args["help"].format(default = default)

    _default_backup_name = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")+".backup"

    def selector_options():
        return {"document_id": Config.OptionSpec(None, {"metavar": "DOCUMENT_ID",
                                                        "help": "Select a document by its DOCUMENT_ID"}),
                "correspondent": Config.OptionSpec(None, {"metavar": "CORRESPONDENT_NAME",
                                                          "type": str,
                                                          "help": "Select documents by their CORRESPONDENT_NAME"}),
                "document_type": Config.OptionSpec(None, {"metavar": "DOCUMENT_TYPE_NAME",
                                                          "type": str,
                                                          "help": "Select documents by their DOCUMENT_TYPE_NAME"}),
                "tag": Config.OptionSpec(None, {"metavar": "TAG_NAME",
                                                "type": str,
                                                "help": "Select documents with tag TAG_NAME"}),
                "storage_path": Config.OptionSpec(None, {"metavar": "STORAGE_PATH_NAME",
                                                          "type": str,
                                                          "help": "Select documents by their STORAGE_PATH_NAME"}),
                "created_year": Config.OptionSpec(None, {"metavar": "YEAR",
                                                         "type": int,
                                                         "help": "Select documents created in YEAR."}),
                "created_month": Config.OptionSpec(None, {"metavar": "MONTH",
                                                         "type": int,
                                                         "help": "Select documents created in MONTH."}),
                "created_day": Config.OptionSpec(None, {"metavar": "DAY",
                                                         "type": int,
                                                         "help": "Select documents created in DAY."}),
                "created_range": Config.OptionSpec(None, {"metavar": "DATE--DATE",
                                                          "type": str,
                                                          "help": "Select documents created in a given range (exclusive), where DATE is of the form YYYY-MM-DD. Example: To get all documents created in April of 2063, you would use '--created-range 2063-03-31--2063-05-01'. To only get documents created before or after a given date, use 'x' instead of date, e.g. 'x--2063-05-01'"}),
                "created_year": Config.OptionSpec(None, {"metavar": "YEAR",
                                                         "type": int,
                                                         "help": "Select documents created in YEAR."}),
                "added_month": Config.OptionSpec(None, {"metavar": "MONTH",
                                                         "type": int,
                                                         "help": "Select documents added in MONTH."}),
                "added_day": Config.OptionSpec(None, {"metavar": "DAY",
                                                         "type": int,
                                                         "help": "Select documents added in DAY."}),
                "added_range": Config.OptionSpec(None, {"metavar": "DATE--DATE",
                                                          "type": str,
                                                          "help": "Select documents added in a given range (exclusive), where DATE is of the form YYYY-MM-DD. Example: To get all documents added in April of 2063, you would use '--added-range 2063-03-31--2063-05-01'. To only get documents added before or after a given date, use 'x' instead of date, e.g. 'x--2063-05-01'"}),
                "asn": Config.OptionSpec(None, {"metavar": "ASN",
                                                "type": int,
                                                "help": "Select document by its ASN"}),
                "title": Config.OptionSpec(None, {"metavar": "TITLE",
                                                "type": str,
                                                "help": "Select document by its TITLE"}),
                "all": Config.OptionSpec(False, {"action": "store_true",
                                                 "help": "Select all documents. WARNING! If you have a lot of documents, this will take a long time."}),
        }
    
    def general_options():
        return {"auth_token": Config.OptionSpec(None, {"metavar": "AUTH_TOKEN",
                                                       "type": str,
                                                       "help": "The auth token to access the REST API of Paperless-ngx. If not specified, postprocessor will try to automagically get it from Paperless-ngx's database directly."}),
                "dry_run": Config.OptionSpec(False, {"action": "store_const",
                                                     "const": True,
                                                     "help": "Don't actually make any changes, just print what would happen. Forces the verbosity level to be at least INFO. (default: {default})"}),
                "skip_validation": Config.OptionSpec(False, {"action": "store_const",
                                                             "const": True,
                                                             "help": "Don't process any validation rules. (default: {default})"}),
                #"dry_run": Config.OptionSpec(False, {"action": "store_true",
                #                                     "help": "Don't actually make any changes, just print what would happen. Forces the verbosity level to be at least INFO. (default: {default})"}),
                "backup": Config.OptionSpec(None, {"type": str,
                                                   "metavar": "FILENAME",
                                                   "help": "Backup file to write any changed values to. If the string DEFAULT is given, one will be automatically generated based on the current date and time. If the path is a directory, the automatically generated file will be stored in that directory. (default: YYYY-MM-DD--HH-MM-SS.backup)"}),
                "postprocessing_tag": Config.OptionSpec(None, {"metavar": "TAG",
                                                               "type": str,
                                                               "help": "A tag to apply if any changes are made during postprocessing. (default: {default})"}),
                "invalid_tag": Config.OptionSpec(None, {"metavar": "TAG",
                                                        "type": str,
                                                        "help": "A tag to apply if the resulting metadata doesn't satisfy any validation rules. (default: {default})"}),
                "verbose": Config.OptionSpec("WARNING", {"type": str,
                                                         "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                                         "help": "The verbosity level for logging. (default: {default})"}),
                "rulesets_dir": Config.OptionSpec("/usr/src/paperless-ngx-postprocessor/rulesets.d", {"metavar": "RULESETS_DIR",
                                                                                                      "type": str,
                                                                                                      "help": "The config directory containing the rulesets for postprocessing. (default: {default})"}),
                "paperless_api_url": Config.OptionSpec("http://localhost:8000/api", {"metavar": "API_URL",
                                                                                     "type": str,
                                                                                     "help": "The full URL to access the Paperless-ngx REST API. (default: {default})"}),
                "paperless_src_dir": Config.OptionSpec("/usr/src/paperless/src", {"metavar": "PAPERLESS_SRC_DIR",
                                                                                  "type": str,
                                                                                  "help": "The directory containing the source for the running instance of paperless. If this is set incorrectly, postprocessor will not be able to automagically acquire the AUTH_TOKEN. (default: {default})"}),
                "ai_usage": Config.OptionSpec("NONE", {"type": str,
                                                       "metavar": "AI_USAGE",
                                                         "choices": ["OLLAMA"],
                                                         #"choices": ["OLLAMA", "OPENAI"],
                                                         "help": "Choose wether you want to make use of now only Ollama is available. Please make sure, that Ollama is up and running and that the Environment Variable OLLAMA_HOST has been set with the proper url.(default: {default})"}),
                "ollama_model": Config.OptionSpec("gemma2", {"type": str,
                                                            "metavar": "OLLAMA_MODEL",
                                                            "type": str,
                                                            "help": "Choose which Ollama Model you want to use. Please be aware, that the Environment Variable PNGX_POSTPROCESSOR_AI_USAGE as well as the Environment Variable OLLAMA_HOST needs to be set in order for this to work. (default: {default})"}),
        }

    def __init__(self, options_spec, use_environment_variables = True):
        #self._default_backup_name = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")+".backup"

        # self.options_spec = {"auth_token": Config.OptionSpec(None, {"metavar": "AUTH_TOKEN",
        #                                                             "type": str,
        #                                                             "help": "The auth token to access the REST API of Paperless-ngx. If not specified, postprocessor will try to automagically get it from Paperless-ngx's database directly."}),
        #                      "dry_run": Config.OptionSpec(False, {"action": "store_const",
        #                                                           "const": True,
        #                                                           "help": "Don't actually make any changes, just print what would happen. Forces the verbosity level to be at least INFO. (default: {default})"}),
        #                      "skip_validation": Config.OptionSpec(False, {"action": "store_const",
        #                                                               "const": True,
        #                                                               "help": "Don't process any validation rules. (default: {default})"}),
        #                      #"dry_run": Config.OptionSpec(False, {"action": "store_true",
        #                      #                                     "help": "Don't actually make any changes, just print what would happen. Forces the verbosity level to be at least INFO. (default: {default})"}),
        #                      "backup": Config.OptionSpec(None, {"nargs": '?',
        #                                                         "type": str,
        #                                                         "const": self._default_backup_name,
        #                                                         "help": "Backup file to write any changed values to. If no filename is given, one will be automatically generated based on the current date and time. If the path is a directory, the automatically generated file will be stored in that directory. (default: {default})"}),
        #                      "postprocessing_tag": Config.OptionSpec(None, {"metavar": "TAG",
        #                                                                     "type": str,
        #                                                                     "help": "A tag to apply if any changes are made during postprocessing. (default: {default})"}),
        #                      "invalid_tag": Config.OptionSpec(None, {"metavar": "TAG",
        #                                                              "type": str,
        #                                                              "help": "A tag to apply if the resulting metadata doesn't satisfy any validation rules. (default: {default})"}),
        #                      "verbose": Config.OptionSpec("WARNING", {"type": str,
        #                                                               "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        #                                                               "help": "The verbosity level for logging. (default: {default})"}),
        #                      "rulesets_dir": Config.OptionSpec("/usr/src/paperless-ngx-postprocessor/rulesets.d", {"metavar": "RULESETS_DIR",
        #                                                                                                            "type": str,
        #                                                                                                            "help": "The config directory containing the rulesets for postprocessing. (default: {default})"}),
        #                      "paperless_api_url": Config.OptionSpec("http://localhost:8000/api", {"metavar": "API_URL",
        #                                                                                           "type": str,
        #                                                                                           "help": "The full URL to access the Paperless-ngx REST API. (default: {default})"}),
        #                      "paperless_src_dir": Config.OptionSpec("/usr/src/paperless/src", {"metavar": "PAPERLESS_SRC_DIR",
        #                                                                                        "type": str,
        #                                                                                        "help": "The directory containing the source for the running instance of paperless. If this is set incorrectly, postprocessor will not be able to automagically acquire the AUTH_TOKEN. (default: {default})"}),
        # }

        self.options_spec = options_spec

        self._options = {}
        for option_name in self.options_spec.keys():
            self._options[option_name] = self.options_spec[option_name].default
            if os.environ.get("PNGX_POSTPROCESSOR_"+option_name.upper()) is not None and use_environment_variables:
                self._options[option_name] = os.environ.get("PNGX_POSTPROCESSOR_"+option_name.upper())
        self._fix_options()
        
    def _fix_options(self):
        if isinstance(self._options.get("dry_run"), str):
            if self._options["dry_run"].lower() in ["f", "false", "no"]:
                self._options["dry_run"] = False
            elif self._options["dry_run"].lower() in ["t", "true", "yes"]:
                self._options["dry_run"] = True
        if isinstance(self._options.get("backup"), str):
            if self._options["backup"].lower() == "default":
                self._options["backup"] = Config._default_backup_name
            else:
                backup_path = Path(self._options["backup"])
                if backup_path.is_dir():
                    self._options["backup"] = str(backup_path / Path(Config._default_backup_name))
        if isinstance(self._options.get("created_range"), str):
            dates = self._options.get("created_range").split("--")
            if len(dates) == 2:
                new_dates = []
                for date_str in dates:
                    try:
                        datetime_obj = dateutil.parser.isoparse(date_str)
                        new_dates.append(datetime_obj.date())
                    except:
                        new_dates.append(None)
                self._options["created_range"] = new_dates
            else:
                self._options["created_range"] = None

        if isinstance(self._options.get("added_range"), str):
            dates = self._options.get("added_range").split("--")
            if len(dates) == 2:
                new_dates = []
                for date_str in dates:
                    try:
                        datetime_obj = dateutil.parser.isoparse(date_str)
                        new_dates.append(datetime_obj.date())
                    except:
                        new_dates.append(None)
                self._options["added_range"] = new_dates
            else:
                self._options["added_range"] = None

    def __getitem__(self, index):
        return self._options[index]

    def __setitem__(self, index, item):
        self._options[index] = item

    def __str__(self):
        return str(self._options)

    def get(self, index, default=None):
        return self._options.get(index, default)

    def values(self):
        return self._options.values()

    def options(self):
        return self._options

    def update_options(self, new_options):
        for option_name in self.options_spec.keys():
            if option_name in new_options and new_options[option_name] is not None:
                self._options[option_name] = new_options[option_name]
        self._fix_options()
