import dateutil.parser
import logging
import os
import requests
import copy
import json
from datetime import date
from pathlib import Path

class PaperlessAPI:
    def __init__(self, api_url, auth_token, paperless_src_dir, logger=None):
        self._logger = logger
        if self._logger is None:
            logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s", level="CRITICAL")
            self._logger = logging.getLogger()
        
        if api_url[-1] == "/":
            api_url = api_url[:-1]

        self._api_url = api_url
        if auth_token is None:
            logging.debug("No auth token specified, trying to acquire automagically...")
            from .get_auth_token import get_auth_token
            auth_token = get_auth_token(paperless_src_dir)
            logging.debug(f"Auth token {auth_token} acquired")

        self._auth_token = auth_token
        self._cache = {}
        self._cachable_types = ["correspondents", "document_types", "storage_paths", "tags"]

    def delete_document_by_id(self, document_id):
        item_type = "documents"
        item_id = document_id
        response = requests.delete(f"{self._api_url}/{item_type}/{item_id}/",
                                   headers = {"Authorization": f"Token {self._auth_token}"})
        return response.ok

    def get_document_metadata_by_id(self, document_id):
        response = requests.get(f"{self._api_url}/documents/{document_id}/metadata/",
                                headers = {"Authorization": f"Token {self._auth_token}"})
        if response.ok:
            return response.json()
        else:
            return {}
        
    def _get_item_by_id(self, item_type, item_id):
        if item_id:
            response = requests.get(f"{self._api_url}/{item_type}/{item_id}/",
                                headers = {"Authorization": f"Token {self._auth_token}"})
            if response.ok:
                return response.json()
        return {}

    def _get_list(self, item_type, query=None):
        # If the given item type has been cached, return it
        if item_type in self._cache and query is None:
            self._logger.debug(f"Returning {item_type} list from cache")
            return self._cache[item_type]

        items = []
        next_url = f"{self._api_url}/{item_type}/"
        if query is not None:
            next_url += f"?{query}"
        while next_url is not None:
            response = requests.get(next_url,
                                    headers = {"Authorization": f"Token {self._auth_token}"})
            if response.ok:
                response_json = response.json()
                items.extend(response_json.get("results"))
                next_url = response_json.get("next")
            else:
                next_url = None
            
        if item_type in self._cachable_types:
            self._cache[item_type] = items

        return items

    def get_item_id_by_name(self, item_type, item_name):
        items = self._get_list(item_type)
        candidates = [item for item in items if item.get("name") == item_name]
        if len(candidates) > 0:
            return candidates[0].get("id")
        return None

    def patch_document(self, document_id, data):
        return requests.patch(f"{self._api_url}/documents/{document_id}/",
                              headers = {"Authorization": f"Token {self._auth_token}", 'Content-type': "application/json" },
                              json = data)

    def get_documents_by_selector_name(self, selector, name):
        # We add the 's' to the selector to turn 'correspondent' into 'correspondents', etc.
        selector_id = self.get_item_id_by_name(selector+"s", name)
        query = f"{selector}__id={selector_id}"
        # Tags is special because the query field is 'tags__id' instead of e.g. 'document_type__id'
        if selector == "tag":
            query = f"{selector}s__id={selector_id}"
        return self._get_list("documents", query) 

    def get_documents_by_field_names(self, **fields):
        allowed_fields = {"correspondent": "correspondent__name__iexact",
                          "document_type": "document_type__name__iexact",
                          "storage_path": "storage_path__name__iexact",
                          "added_year": "added__year",
                          "added_month": "added__month",
                          "added_day": "added_day",
                          "asn": "archive_serial_number",
                          "title": "title__iexact",
                          "created_year": "created__year",
                          "created_month": "created__month",
                          "created_day": "created__day",
                          "custom_fields": "custom_fields"
        }

        queries = []
        for key in allowed_fields.keys():
            if key in fields.keys() and fields[key] is not None:
                queries.append(f"{allowed_fields[key]}={fields[key]}")

        if (isinstance(fields.get("added_range"), (tuple, list)) and
            len(fields.get("added_range")) == 2):
            if isinstance(fields["added_range"][0], date):
                queries.append(f"added__date__gt={fields['added_range'][0].strftime('%F')}")
            if isinstance(fields["added_range"][1], date):
                queries.append(f"added__date__lt={fields['added_range'][1].strftime('%F')}")

        if (isinstance(fields.get("created_range"), (tuple, list)) and
            len(fields.get("created_range")) == 2):
            if isinstance(fields["created_range"][0], date):
                queries.append(f"created__date__gt={fields['created_range'][0].strftime('%F')}")
            if isinstance(fields["created_range"][1], date):
                queries.append(f"created__date__lt={fields['created_range'][1].strftime('%F')}")


        if isinstance(fields.get("added_date_object"), date):
            queries.append(f"added__year={fields['added_date_object'].year}&added__month={fields['added_date_object'].month}&added__day={fields['added_date_object'].day}")

        if isinstance(fields.get("created_date_object"), date):
            queries.append(f"created__year={fields['created_date_object'].year}&created__month={fields['created_date_object'].month}&created__day={fields['created_date_object'].day}")

        query = "&".join(queries)
        self._logger.debug(f"Running query '{query}'")
        return self._get_list("documents", query)


    # def get_documents_from_query(self, query):
    #     return self._get_list("documents", query)

    def get_all_documents(self):
        return self._get_list("documents")

    def get_document_by_id(self, document_id):
        return self._get_item_by_id("documents", document_id)
        
    def get_correspondent_by_id(self, correspondent_id):
        return self._get_item_by_id("correspondents", correspondent_id)

    def get_document_type_by_id(self, document_type_id):
        return self._get_item_by_id("document_types", document_type_id)

    def get_storage_path_by_id(self, storage_path_id):
        return self._get_item_by_id("storage_paths", storage_path_id)
    
    def get_tag_by_id(self, tag_id):
        return self._get_item_by_id("tags", tag_id)

    def get_metadata_in_filename_format(self, metadata):
        new_metadata = {}
        new_metadata["document_id"] = metadata["id"]
        new_metadata["correspondent"] = (self.get_correspondent_by_id(metadata["correspondent"])).get("name")
        new_metadata["document_type"] = (self.get_document_type_by_id(metadata["document_type"])).get("name")
        new_metadata["storage_path"] = (self.get_storage_path_by_id(metadata["storage_path"])).get("name")
        new_metadata["asn"] = metadata["archive_serial_number"]
        new_metadata["tag_list"] = [self.get_tag_by_id(tag)["name"] for tag in metadata["tags"]]
        new_metadata["title"] = metadata["title"]
        new_metadata["created"] = metadata["created"]
        created_date = dateutil.parser.isoparse(new_metadata["created"])
        new_metadata["created_year"] = f"{created_date.year:04d}"
        new_metadata["created_month"] = f"{created_date.month:02d}"
        new_metadata["created_day"] = f"{created_date.day:02d}"
        new_metadata["created_date"] = created_date.strftime("%F") # %F means YYYY-MM-DD
        new_metadata["created_date_object"] = created_date
        new_metadata["added"] = metadata["added"]
        added_date = dateutil.parser.isoparse(new_metadata["added"])
        new_metadata["added_year"] = f"{added_date.year:04d}"
        new_metadata["added_month"] = f"{added_date.month:02d}"
        new_metadata["added_day"] = f"{added_date.day:02d}"
        new_metadata["added_date"] = added_date.strftime("%F")
        new_metadata["added_date_object"] = added_date
        new_metadata["custom_fields"] = metadata["custom_fields"]
        
        return new_metadata

    def get_metadata_from_filename_format(self, metadata_in_filename_format):
        result = {}
        result["id"] = metadata_in_filename_format["document_id"]
        result["correspondent"] = self.get_item_id_by_name("correspondents", metadata_in_filename_format["correspondent"])
        result["document_type"] = self.get_item_id_by_name("document_types", metadata_in_filename_format["document_type"])
        result["storage_path"] = self.get_item_id_by_name("storage_paths", metadata_in_filename_format["storage_path"])
        result["archive_serial_number"] = metadata_in_filename_format["asn"]
        result["tags"] = [self.get_item_id_by_name("tags", tag_name) for tag_name in metadata_in_filename_format["tag_list"]]
        result["title"] = metadata_in_filename_format["title"]
        result["created"] = metadata_in_filename_format["created"]
        result["created_date"] = dateutil.parser.isoparse(metadata_in_filename_format["created"]).strftime("%F")
        result["added"] = metadata_in_filename_format["added"]
        result["custom_fields"] = metadata_in_filename_format["custom_fields"]
        
        return result
        
    def get_metadata_for_post_consume_script(self, document_id):
        result = {}
        document = self.get_document_by_id(document_id)
        document_metadata = self.get_document_metadata_by_id(document_id)
        result["DOCUMENT_ID"] = str(document_id)
        result["DOCUMENT_FILE_NAME"] = document.get("original_file_name")
        result["DOCUMENT_CREATED"] = document.get("created").replace("T", " ")
        result["DOCUMENT_MODIFIED"] = document.get("modified").replace("T", " ")
        result["DOCUMENT_ADDED"] = document.get("added").replace("T", " ")        
        result["DOCUMENT_SOURCE_PATH"] = str(Path(os.environ.get("MEDIA_ROOT_DIR")) / Path("documents/originals") / Path(document_metadata.get("media_filename")))
        if document_metadata.get("has_archive_version"):            
            result["DOCUMENT_ARCHIVE_PATH"] = str(Path(os.environ.get("MEDIA_ROOT_DIR")) / Path("documents/archive") / Path(document_metadata.get("archive_media_filename")))
        else:
            result["DOCUMENT_ARCHIVE_PATH"] = None
        result["DOCUMENT_CORRESPONDENT"] = self.get_correspondent_by_id(document.get("correspondent")).get("name")
        result["DOCUMENT_TAGS"] = ",".join([self.get_tag_by_id(tag_id).get("name") for tag_id in document.get("tags")])

        return result

    def get_customfield_from_name(self, customfield_name):
        result = {}

        # rework underscore's into url spaces
        url_reworked_customfield_name = customfield_name.replace("_","%20")

        response = requests.get(f"{self._api_url}/custom_fields/?name__icontains={url_reworked_customfield_name}", headers = {"Authorization": f"Token {self._auth_token}"})

        if len(response.json().get("results")) > 1:
            self._logger.error("Found more than one custom_field with specified name in filter. Name has to be unique.")
        elif len(response.json().get("results")) == 0:
            self._logger.error("Found no custom fields with this name.")
        else:
            self._logger.debug(f"Found custom_field: \"{response.json().get('results')[0].get('name')}\" with id {response.json().get('results')[0].get('id')}. Building custom_fields object definition.")

        result = copy.deepcopy(response.json().get("results")[0])

        return result
