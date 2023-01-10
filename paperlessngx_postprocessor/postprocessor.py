import calendar
import dateutil.parser
import jinja2
import logging
import regex
import yaml
from datetime import datetime
from pathlib import Path

from .paperless_api import PaperlessAPI

class DocumentRuleProcessor:
    def __init__(self, spec, logger = None):
        self._logger = logger
        if self._logger is None:
            logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s", level="CRITICAL")
            self._logger = logging.getLogger()

        self.name = list(spec.keys())[0]
        self._match = spec[self.name].get("match")
        self._metadata_regex = spec[self.name].get("metadata_regex")
        self._metadata_postprocessing = spec[self.name].get("metadata_postprocessing")
        #self._title_format = spec[self.name].get("title_format")

        self._env = jinja2.Environment()
        self._env.filters["expand_two_digit_year"] = self._expand_two_digit_year
        self._env.filters["regex_match"] = self._jinja_filter_regex_match
        self._env.filters["regex_sub"] = self._jinja_filter_regex_sub

    def matches(self, metadata):
        if type(self._match) is str:
            template = self._env.from_string(self._match)
            return template.render(**metadata) == "True"
        elif type(self._match) is bool:
            return self._match
        else:
            return False

    def _normalize_month(self, new_month, old_month):
        try:
            if int(new_month) >= 1 and int(new_month) <= 12:
                return f"{int(new_month):02d}"
        except ValueError:
            month_abbr_lower = [month.lower() for month in calendar.month_abbr]
            month_name_lower = [month.lower() for month in calendar.month_name]
            if new_month.lower() in month_abbr_lower:
                return f"{month_abbr_lower.index(new_month.lower()):02d}"
            elif new_month.lower() in month_name_lower:
                return f"{month_name_lower.index(new_month.lower()):02d}"
        return old_month

    def _normalize_day(self, new_day, old_day):
        try:
            return f"{int(new_day):02d}"
        except:
            return old_day
    
    def _expand_two_digit_year(self, year, prefix=None):
        if prefix is None:
            prefix = str(datetime.now().year)[0:-2]
        elif type(prefix) is int:
            prefix = prefix*100
        if int(year) < 100:
            return f"{prefix}{int(year):02}"
        else:
            return f"{year}"

    def _jinja_filter_regex_match(self, string, pattern):
        '''Custom jinja filter for regex matching'''
        if regex.match(pattern, string):
            return True
        else:
            return False

    def _jinja_filter_regex_sub(self, string, pattern, repl):
        '''Custom jinja filter for regex substitution'''
        return regex.sub(pattern, repl, string)
    
    def _normalize_created_dates(self, new_metadata, old_metadata):
        result = new_metadata.copy()
        #if "created_year" in metadata.keys():
        try:
            result["created_year"] = str(int(new_metadata["created_year"]))
        except:
            result["created_year"] = old_metadata["created_year"]
        #if "created_month" in metadata.keys():
        result["created_month"] = self._normalize_month(new_metadata["created_month"], old_metadata["created_month"])
        #if "created_day" in metadata.keys():
        result["created_day"] = self._normalize_day(new_metadata["created_day"], old_metadata["created_day"])

        original_created_date = dateutil.parser.isoparse(old_metadata["created"])
        new_created_date = datetime(int(result["created_year"]), int(result["created_month"]), int(result["created_day"]), 12, tzinfo=original_created_date.tzinfo)
        result["created"] = new_created_date.isoformat()
        result["created_date"] = new_created_date.strftime("%F") # %F means YYYY-MM-DD
        
        return result

        
    def get_new_metadata(self, metadata, content):
        read_only_metadata_keys = ["correspondent",
                                   "document_type",
                                   "storage_path",
                                   "tag_list",
                                   "added",
                                   "added_year",
                                   "added_month",
                                   "added_day"]        
        read_only_metadata = {key: metadata[key] for key in read_only_metadata_keys if key in metadata}
        writable_metadata_keys = list(set(metadata.keys()) - set(read_only_metadata_keys))
        writable_metadata = {key: metadata[key] for key in writable_metadata_keys if key in metadata}
        
        # Extract the regex_data
        if self._metadata_regex is not None:
            match_object = regex.search(self._metadata_regex, content)
            if match_object is not None:
                regex_data = match_object.groupdict()
                #writable_metadata.update(match_object.groupdict())
                writable_metadata.update([(k, regex_data[k]) for k in regex_data if regex_data[k] is not None])
                writable_metadata = self._normalize_created_dates(writable_metadata, metadata)
                self._logger.debug(f"Regex results are {writable_metadata}")
            else:
                self._logger.warning(f"Regex '{self._metadata_regex}' for '{self.name}' didn't match")
                
        # Cycle throguh the postprocessing rules
        if self._metadata_postprocessing is not None:
            for variable_name in self._metadata_postprocessing.keys():
                try:
                    old_value = writable_metadata.get(variable_name)
                    merged_metadata = {**writable_metadata, **read_only_metadata}
                    template = self._env.from_string(self._metadata_postprocessing[variable_name])
                    writable_metadata[variable_name] = template.render(**merged_metadata)                    
                    writable_metadata = self._normalize_created_dates(writable_metadata, metadata)
                    self._logger.debug(f"Updating '{variable_name}' using template {self._metadata_postprocessing[variable_name]} and metadata {merged_metadata}\n: '{old_value}'->'{writable_metadata[variable_name]}'")
                except Exception as e:
                    self._logger.error(f"Error parsing template {self._metadata_postprocessing[variable_name]} for {variable_name} using metadata {merged_metadata}: {e}")

        else:
            self._logger.debug(f"No postprocessing rules found for rule {self.name}")

        return {**writable_metadata, **read_only_metadata}



class Postprocessor:
    def __init__(self, api, rules_dir, postprocessing_tag = None, dry_run = False, logger = None):
        self._logger = logger
        if self._logger is None:
            logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s", level="CRITICAL")
            self._logger = logging.getLogger()

        self._api = api
        self._rules_dir = Path(rules_dir)
        if postprocessing_tag is not None:
            self._postprocessing_tag_id = self._api.get_item_id_by_name("tags", postprocessing_tag)
        else:
            self._postprocessing_tag_id = None
        self._dry_run = dry_run

        self._processors = []
    
        for filename in sorted(list(self._rules_dir.glob("*.yml"))):
            if filename.is_file():
                with open(filename, "r") as yaml_file:
                    try:
                        yaml_documents = yaml.safe_load_all(yaml_file)
                        for yaml_document in yaml_documents:
                            self._processors.append(DocumentRuleProcessor(yaml_document, self._logger))
                    except Exception as e:
                        self._logger.warning(f"Unable to parse yaml in {filename}: {e}")
        self._logger.debug(f"Loaded {len(self._processors)} rules")

        
    def _get_new_metadata_in_filename_format(self, metadata_in_filename_format, content):
        new_metadata = metadata_in_filename_format.copy()
        
        for processor in self._processors:
            if processor.matches(metadata_in_filename_format):
                self._logger.debug(f"Rule {processor.name} matches")
                new_metadata = processor.get_new_metadata(metadata_in_filename_format, content)
                metadata_in_filename_format = {**metadata_in_filename_format, **new_metadata}
            else:
                self._logger.debug(f"Rule {processor.name} does not match")

        return new_metadata


    def postprocess(self, documents):
        backup_documents = []
        for document in documents:
            metadata_in_filename_format = self._api.get_metadata_in_filename_format(document)
            self._logger.debug(f"metadata_in_filename_format={metadata_in_filename_format}")
            new_metadata_in_filename_format = self._get_new_metadata_in_filename_format(metadata_in_filename_format, document["content"])
            self._logger.debug(f"new_metadata_in_filename_format={new_metadata_in_filename_format}")
            if len([key for key in metadata_in_filename_format.keys() if metadata_in_filename_format[key] != new_metadata_in_filename_format.get(key)]) > 0:
                new_metadata = self._api.get_metadata_from_filename_format(new_metadata_in_filename_format)
                # differences should be a list of keys that have changed
                differences = [key for key in new_metadata.keys() if new_metadata[key] != document[key]]
                if len(differences) > 0 and self._postprocessing_tag_id is not None:
                    new_metadata["tags"].append(self._postprocessing_tag_id)
                    differences = [key for key in new_metadata.keys() if new_metadata[key] != document[key]]
                if len(differences) > 0:
                    self._logger.info(f"Changes for document_id={document['id']}:")
                    for key in differences:
                        self._logger.info(f" {key}: '{document[key]}' --> '{new_metadata[key]}'")                        
                    if not self._dry_run:
                        differences.append("created_date")
                        self._api.patch_document(document["id"], {key: new_metadata[key] for key in differences})
                        backup_data = {key: document[key] for key in differences}
                        backup_data["id"] = document["id"]
                        backup_documents.append(backup_data)                        
                else:
                    self._logger.info(f"No changes for document_id={document['id']}")
            else:
                self._logger.info(f"No changes for document_id={document['id']}")
            
        return backup_documents
        
#         # if "created_year" in regex_data.keys():
#         #     metadata["created_year"] = regex_data["created_year"]
#         # if "created_month" in regex_data.keys():
#         #     metadata["created_month"] = self._normalize_month(regex_data["created_month"], metadata["created_month"])
#         # if "created_day" in regex_data.keys():
#         #     metadata["created_day"] = self._normalize_day(regex_data["created_day"], metadata["created_day"])

#         # if self._created_date_adjustments is not None:
#         #     new_created_date = {}
#         #     merged_metadata = {**regex_data, **metadata}
#         #     if "created_year" in self._created_date_adjustments.keys():
#         #         template = self._env.from_string(self._created_date_adjustments["created_year"])
#         #         new_created_date["created_year"] = template.render(**merged_metadata)
#         #     if "created_month" in self._created_date_adjustments.keys():
#         #         template = self._env.from_string(self._created_date_adjustments["created_month"])
#         #         new_created_date["created_month"] = self._normalize_month(template.render(**merged_metadata), metadata["created_month"])
#         #     if "created_day" in self._created_date_adjustments.keys():
#         #         template = self._env.from_string(self._created_date_adjustments["created_day"])
#         #         new_created_date["created_day"] = self._normalize_day(template.render(**merged_metadata), metadata["created_year"])

#         #     metadata.update(new_created_date)        
                
#         # original_created_date = dateutil.parser.isoparse(metadata["created"])
#         # new_created_date = datetime(int(metadata["created_year"]), int(metadata["created_month"]), int(metadata["created_day"]), tzinfo=original_created_date.tzinfo)
#         # metadata["created"] = new_created_date.isoformat()
#         # #result["created"] = new_created_date.isoformat()
#         # result["created_date"] = new_created_date.strftime("%F") # %F means YYYY-MM-DD
            
#         # if self._title_format is not None:
#         #     try:
#         #         merged_metadata = {**regex_data, **metadata}
#         #         # print(f"Creating new title from {merged_metadata}")
#         #         template = self._env.from_string(self._title_format)
#         #         result["title"] = template.render(**merged_metadata)
#         #     except:
#         #         print(f"Error parsing template \"{self._title_format}\" using data {merged_metadata}")
#         #         # FIXME print the actual exception error here

#         # return result


# class PaperlessPostprocessor:
#     def __init__(self, config_dir, logger=None):
#         self._logger = logger
#         if self._logger is None:
#             self._logger = logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s", level="CRITICAL")

#         self._processors = []

#         config_dir_path = Path(config_dir)
        
#         for filename in config_dir_path.glob("*"):
#             if filename.is_file():
#                 with open(filename, "r") as yaml_file:
#                     try:
#                         yaml_documents = yaml.safe_load_all(yaml_file)
#                         for yaml_document in yaml_documents:
#                             self._processors.append(DocumentRuleProcessor(yaml_document))
#                     except:
#                         print(f"Unable to parse yaml in {filename}")
#         logger.debug(f"Loaded {len(self._processors)} rules")

                
