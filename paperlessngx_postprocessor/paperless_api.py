import dateutil.parser
import logging
import os
import requests
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
        response = requests.get(f"{self._api_url}/{item_type}/{item_id}/",
                                headers = {"Authorization": f"Token {self._auth_token}"})
        if response.ok:
            return response.json()
        else:
            return {}

    def _get_list(self, item_type, query=None):
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
            
        return items

    def get_item_id_by_name(self, item_type, item_name):
        items = self._get_list(item_type)
        candidates = [item for item in items if item.get("name") == item_name]
        if len(candidates) > 0:
            return candidates[0].get("id")
        return None

    def patch_document(self, document_id, data):
        return requests.patch(f"{self._api_url}/documents/{document_id}/",
                              headers = {"Authorization": f"Token {self._auth_token}"},
                              data = data)

    def get_documents_by_selector_name(self, selector, name):
        # We add the 's' to the selector to turn 'correspondent' into 'correspondents', etc.
        selector_id = self.get_item_id_by_name(selector+"s", name)
        query = f"{selector}__id={selector_id}"
        # Tags is special because the query field is 'tags__id' instead of e.g. 'document_type__id'
        if selector == "tag":
            query = f"{selector}s__id={selector_id}"
        return self._get_list("documents", query) 

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
        new_metadata["added"] = metadata["added"]
        added_date = dateutil.parser.isoparse(new_metadata["added"])
        new_metadata["added_year"] = f"{added_date.year:04d}"
        new_metadata["added_month"] = f"{added_date.month:02d}"
        new_metadata["added_day"] = f"{added_date.day:02d}"
        
        return new_metadata

    def get_metadata_from_filename_format(self, metadata_in_filename_format):
        result = {}
        result["correspondent"] = self.get_item_id_by_name("correspondents", metadata_in_filename_format["correspondent"])
        result["document_type"] = self.get_item_id_by_name("document_types", metadata_in_filename_format["document_type"])
        result["storage_path"] = self.get_item_id_by_name("storage_paths", metadata_in_filename_format["storage_path"])
        result["archive_serial_number"] = metadata_in_filename_format["asn"]
        result["tags"] = [self.get_item_id_by_name("tags", tag_name) for tag_name in metadata_in_filename_format["tag_list"]]
        result["title"] = metadata_in_filename_format["title"]
        result["created"] = metadata_in_filename_format["created"]
        result["created_date"] = dateutil.parser.isoparse(metadata_in_filename_format["created"]).strftime("%F")
        result["added"] = metadata_in_filename_format["added"]
        
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
