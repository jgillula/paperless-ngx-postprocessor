import os
from datetime import datetime
from pathlib import Path

class Config:
    class OptionSpec:
        def __init__(self, default, argparse_args):
            self.default = default
            self.argparse_args = argparse_args

            if "help" in self.argparse_args:
                self.argparse_args["help"] = self.argparse_args["help"].format(default = default)
            
    
    def __init__(self):
        self._default_backup_name = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")+".backup"
        
        self.options_spec = {"auth_token": Config.OptionSpec(None, {"metavar": "AUTH_TOKEN",
                                                                    "type": str,
                                                                    "help": "The auth token to access the REST API of Paperless-ngx. If not specified, postprocessor will try to automagically get it from Paperless-ngx's database directly."}),
                             "dry_run": Config.OptionSpec(False, {"action": "store_const",
                                                                  "const": True,
                                                                  "help": "Don't actually make any changes, just print what would happen. Forces the verbosity level to be at least INFO. (default: {default})"}),
                             #"dry_run": Config.OptionSpec(False, {"action": "store_true",
                             #                                     "help": "Don't actually make any changes, just print what would happen. Forces the verbosity level to be at least INFO. (default: {default})"}),
                             "backup": Config.OptionSpec(None, {"nargs": '?',
                                                                "type": str,
                                                                "const": self._default_backup_name,
                                                                "help": "Backup file to write any changed values to. If no filename is given, one will be automatically generated based on the current date and time. If the path is a directory, the automatically generated file will be stored in that directory. (default: {default})"}),
                             "postprocessing_tag": Config.OptionSpec(None, {"metavar": "TAG",
                                                                            "type": str,
                                                                            "help": "A tag to apply if any changes are made during postprocessing. (default: {default})"}),
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
        }

        self._options = {}
        for option_name in self.options_spec.keys():
            self._options[option_name] = self.options_spec[option_name].default
            if os.environ.get("PNGX_POSTPROCESSOR_"+option_name.upper()) is not None:
                self._options[option_name] = os.environ.get("PNGX_POSTPROCESSOR_"+option_name.upper())
        self._fix_options()
        
    def _fix_options(self):
        if isinstance(self._options["dry_run"], str):
            if self._options["dry_run"].lower() in ["f", "false", "no"]:
                self._options["dry_run"] = False
            elif self._options["dry_run"].lower() in ["t", "true", "yes"]:
                self._options["dry_run"] = True
        if isinstance(self._options["backup"], str):
            if self._options["backup"].lower() in ["t", "true", "yes"]:
                self._options["backup"] = self._default_backup_name
            elif self._options["backup"].lower() in ["f", "false", "no"]:
                self._options["backup"] = None
            else:
                backup_path = Path(self._options["backup"])
                if backup_path.is_dir():
                    self._options["backup"] = str(backup_path / Path(self._default_backup_name))

    def __getitem__(self, index):
        return self._options[index]

    def __setitem__(self, index, item):
        self._options[index] = item

    def __str__(self):
        return str(self._options)
        
    def update_options(self, new_options):
        for option_name in self.options_spec.keys():
            if option_name in new_options and new_options[option_name] is not None:
                self._options[option_name] = new_options[option_name]
        self._fix_options()
